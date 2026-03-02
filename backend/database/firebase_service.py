"""
Firebase Firestore Service
Phase 7: Database persistence layer

Replaces in-memory storage with Firestore for:
✅ Session persistence
✅ User profiles
✅ Analytics history
✅ Multi-instance support

SECURITY:
✅ Collections protected with Firestore security rules
✅ User isolation (query by user_id)
✅ Automatic cleanup of expired sessions
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging
import os
import asyncio

logger = logging.getLogger("firebase_service")


class FirebaseManager:
    """
    Firestore database manager
    Handles all persistence operations
    """
    
    _instance = None
    _db = None
    
    def __new__(cls):
        """Singleton pattern - one Firebase connection"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase already initialized
            if firebase_admin._apps:
                self._db = firestore.client()
                logger.info("Firebase already initialized, using existing connection")
            else:
                # Initialize with service account key
                cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.js")
                
                if not os.path.exists(cred_path):
                    raise FileNotFoundError(f"Service account key not found: {cred_path}")
                
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                self._db = firestore.client()
                logger.info("Firebase initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise
    
    @property
    def db(self):
        """Get Firestore client"""
        return self._db
    
    # ========================================================================
    # SESSION OPERATIONS
    # ========================================================================
    
    async def create_session(self, session_id: str, session_data: dict) -> bool:
        """
        Create a new session in Firestore
        
        Args:
            session_id: Unique session identifier
            session_data: Session data dict
        
        Returns:
            True if successful
        """
        try:
            # Add timestamp
            session_data["created_at"] = datetime.utcnow()
            session_data["expires_at"] = datetime.utcnow() + timedelta(days=7)
            
            # Write to Firestore asynchronously
            await asyncio.to_thread(
                self._db.collection("sessions").document(session_id).set(session_data)
            )
            
            logger.info(f"Session created: {session_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve session from Firestore
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session data dict or None if not found
        """
        try:
            doc = await asyncio.to_thread(
                lambda: self._db.collection("sessions").document(session_id).get()
            )
            
            if doc.exists:
                return doc.to_dict()
            
            logger.warning(f"Session not found: {session_id}")
            return None
        
        except Exception as e:
            logger.error(f"Error retrieving session: {str(e)}")
            return None
    
    async def update_session(self, session_id: str, updates: dict) -> bool:
        """
        Update existing session
        
        Args:
            session_id: Session identifier
            updates: Dict of fields to update
        
        Returns:
            True if successful
        """
        try:
            updates["updated_at"] = datetime.utcnow()
            
            await asyncio.to_thread(
                self._db.collection("sessions").document(session_id).update(updates)
            )
            
            logger.info(f"Session updated: {session_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session from Firestore
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if successful
        """
        try:
            await asyncio.to_thread(
                self._db.collection("sessions").document(session_id).delete()
            )
            
            logger.info(f"Session deleted: {session_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> list:
        """
        Get all valid sessions for a user
        
        Args:
            user_id: User identifier
        
        Returns:
            List of session dicts
        """
        try:
            docs = await asyncio.to_thread(
                lambda: self._db.collection("sessions")
                         .where("user_id", "==", user_id)
                         .where("is_valid", "==", True)
                         .stream()
            )
            
            sessions = [doc.to_dict() for doc in docs]
            logger.info(f"Found {len(sessions)} sessions for user {user_id}")
            return sessions
        
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            return []
    
    async def find_session_by_refresh_token(self, refresh_token: str) -> tuple:
        """
        Find session by refresh token (for token refresh flow)
        
        Args:
            refresh_token: JWT refresh token
        
        Returns:
            Tuple of (session_id, session_data) or (None, None)
        """
        try:
            docs = await asyncio.to_thread(
                lambda: self._db.collection("sessions")
                         .where("jwt_refresh_token", "==", refresh_token)
                         .limit(1)
                         .stream()
            )
            
            docs_list = list(docs)
            if docs_list:
                doc = docs_list[0]
                return (doc.id, doc.to_dict())
            
            return (None, None)
        
        except Exception as e:
            logger.error(f"Error finding session by refresh token: {str(e)}")
            return (None, None)
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Delete sessions older than 7 days
        Called periodically to clean up old data
        
        Returns:
            Number of sessions deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            
            docs = await asyncio.to_thread(
                lambda: self._db.collection("sessions")
                         .where("created_at", "<", cutoff_date)
                         .stream()
            )
            
            count = 0
            for doc in docs:
                await asyncio.to_thread(doc.reference.delete())
                count += 1
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")
            
            return count
        
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return 0
    
    # ========================================================================
    # USER OPERATIONS
    # ========================================================================
    
    async def create_or_update_user(self, user_id: str, user_data: dict) -> bool:
        """
        Create or update user profile
        
        Args:
            user_id: User identifier
            user_data: User data dict
        
        Returns:
            True if successful
        """
        try:
            user_data["updated_at"] = datetime.utcnow()
            
            if not user_data.get("created_at"):
                user_data["created_at"] = datetime.utcnow()
            
            await asyncio.to_thread(
                self._db.collection("users").document(user_id).set(user_data, merge=True)
            )
            
            logger.info(f"User created/updated: {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error creating/updating user: {str(e)}")
            return False
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """
        Retrieve user profile
        
        Args:
            user_id: User identifier
        
        Returns:
            User data dict or None
        """
        try:
            doc = await asyncio.to_thread(
                lambda: self._db.collection("users").document(user_id).get()
            )
            
            return doc.to_dict() if doc.exists else None
        
        except Exception as e:
            logger.error(f"Error retrieving user: {str(e)}")
            return None
    
    # ========================================================================
    # ANALYTICS OPERATIONS
    # ========================================================================
    
    async def save_analytics(self, user_id: str, analytics_data: dict) -> bool:
        """
        Save analytics snapshot for user
        
        Args:
            user_id: User identifier
            analytics_data: Analytics dict
        
        Returns:
            True if successful
        """
        try:
            doc_id = f"{user_id}_{datetime.utcnow().strftime('%Y-%m-%d')}"
            
            analytics_data["user_id"] = user_id
            analytics_data["calculated_at"] = datetime.utcnow()
            
            await asyncio.to_thread(
                self._db.collection("analytics").document(doc_id).set(analytics_data, merge=True)
            )
            
            logger.info(f"Analytics saved: {doc_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving analytics: {str(e)}")
            return False
    
    async def get_latest_analytics(self, user_id: str) -> Optional[Dict]:
        """
        Get most recent analytics for user
        
        Args:
            user_id: User identifier
        
        Returns:
            Analytics dict or None
        """
        try:
            docs = await asyncio.to_thread(
                lambda: self._db.collection("analytics")
                         .where("user_id", "==", user_id)
                         .order_by("calculated_at", direction=firestore.Query.DESCENDING)
                         .limit(1)
                         .stream()
            )
            
            docs_list = list(docs)
            if docs_list:
                return docs_list[0].to_dict()
            
            return None
        
        except Exception as e:
            logger.error(f"Error retrieving analytics: {str(e)}")
            return None
    
    # ========================================================================
    # INSIGHTS OPERATIONS
    # ========================================================================
    
    async def save_insights(self, user_id: str, insights_data: dict) -> bool:
        """
        Save AI insights for user
        
        Args:
            user_id: User identifier
            insights_data: Insights dict
        
        Returns:
            True if successful
        """
        try:
            doc_id = f"{user_id}_{datetime.utcnow().strftime('%Y-%m-%d')}"
            
            insights_data["user_id"] = user_id
            insights_data["generated_at"] = datetime.utcnow()
            
            await asyncio.to_thread(
                self._db.collection("insights").document(doc_id).set(insights_data, merge=True)
            )
            
            logger.info(f"Insights saved: {doc_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving insights: {str(e)}")
            return False
    
    async def get_latest_insights(self, user_id: str) -> Optional[Dict]:
        """
        Get most recent insights for user
        
        Args:
            user_id: User identifier
        
        Returns:
            Insights dict or None
        """
        try:
            docs = await asyncio.to_thread(
                lambda: self._db.collection("insights")
                         .where("user_id", "==", user_id)
                         .order_by("generated_at", direction=firestore.Query.DESCENDING)
                         .limit(1)
                         .stream()
            )
            
            docs_list = list(docs)
            if docs_list:
                return docs_list[0].to_dict()
            
            return None
        
        except Exception as e:
            logger.error(f"Error retrieving insights: {str(e)}")
            return None


# Global Firebase instance
firebase_db = FirebaseManager()


async def get_firebase() -> FirebaseManager:
    """Dependency injection for FastAPI"""
    return firebase_db
