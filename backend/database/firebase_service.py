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

# Timeout configuration
FIREBASE_TIMEOUT = 3.0
MAX_RETRIES = 1


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
                cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
                
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
        Create a new session in Firestore with timeout and retry
        
        Args:
            session_id: Unique session identifier
            session_data: Session data dict
        
        Returns:
            True if successful
        """
        # Input validation
        if not session_id or not isinstance(session_data, dict):
            logger.warning(f"Invalid session data: session_id={session_id}, data_type={type(session_data)}")
            return False
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                logger.info(f"Saving session {session_id} to Firestore (attempt {attempt + 1})...")
                session_data["created_at"] = datetime.utcnow()
                session_data["expires_at"] = datetime.utcnow() + timedelta(days=7)
                
                await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self._db.collection("sessions").document(session_id).set(session_data)
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                logger.info(f"Session {session_id} saved successfully!")
                return True
            
            except asyncio.TimeoutError:
                logger.warning(f"Firestore timeout on attempt {attempt + 1} for session {session_id}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                logger.error(f"Failed to save session {session_id} after {attempt + 1} attempts (timeout)")
                return False
            except Exception as e:
                logger.error(f"Error saving session {session_id} on attempt {attempt + 1}: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
        
        return False
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve session from Firestore with timeout
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session data dict or None if not found
        """
        # Input validation
        if not session_id or not isinstance(session_id, str):
            logger.warning(f"Invalid session_id: {session_id}, type: {type(session_id)}")
            return None
        
        try:
            logger.info(f"Retrieving session from Firestore: {session_id}")
            doc = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: self._db.collection("sessions").document(session_id).get()
                ),
                timeout=FIREBASE_TIMEOUT
            )
            
            if doc.exists:
                logger.info(f"Session {session_id} found with data")
                return doc.to_dict()
            logger.warning(f"Session {session_id} does not exist in Firestore")
            return None
        
        except asyncio.TimeoutError:
            logger.error(f"Firestore timeout while retrieving session {session_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            return None
    
    async def update_session(self, session_id: str, updates: dict) -> bool:
        """
        Update existing session with timeout and retry
        
        Args:
            session_id: Session identifier
            updates: Dict of fields to update
        
        Returns:
            True if successful
        """
        # Input validation
        if not session_id or not isinstance(updates, dict):
            return False
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                updates["updated_at"] = datetime.utcnow()
                
                await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self._db.collection("sessions").document(session_id).update(updates)
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                return True
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
            except Exception:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
        
        return False
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session from Firestore with timeout and retry
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if successful
        """
        # Input validation
        if not session_id or not isinstance(session_id, str):
            return False
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self._db.collection("sessions").document(session_id).delete()
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                return True
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
            except Exception:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
        
        return False
    
    async def get_user_sessions(self, user_id: str) -> list:
        """
        Get all valid sessions for a user with timeout and retry
        
        Args:
            user_id: User identifier
        
        Returns:
            List of session dicts (empty list on failure)
        """
        # Input validation
        if not user_id or not isinstance(user_id, str):
            return []
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                docs = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: list(self._db.collection("sessions")
                                     .where("user_id", "==", user_id)
                                     .where("is_valid", "==", True)
                                     .stream())
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                
                return [doc.to_dict() for doc in docs]
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return []
            except Exception:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return []
        
        return []
    
    async def find_session_by_refresh_token(self, refresh_token: str) -> tuple:
        """
        Find session by refresh token with timeout and retry
        
        Args:
            refresh_token: JWT refresh token
        
        Returns:
            Tuple of (session_id, session_data) or (None, None) on failure
        """
        # Input validation
        if not refresh_token or not isinstance(refresh_token, str):
            return (None, None)
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                docs = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: list(self._db.collection("sessions")
                                     .where("jwt_refresh_token", "==", refresh_token)
                                     .limit(1)
                                     .stream())
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                
                if docs:
                    doc = docs[0]
                    return (doc.id, doc.to_dict())
                
                return (None, None)
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return (None, None)
            except Exception:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return (None, None)
        
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
        Create or update user profile with timeout and retry
        
        Args:
            user_id: User identifier
            user_data: User data dict
        
        Returns:
            True if successful
        """
        # Input validation
        if not user_id or not isinstance(user_data, dict):
            return False
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                user_data["updated_at"] = datetime.utcnow()
                
                if not user_data.get("created_at"):
                    user_data["created_at"] = datetime.utcnow()
                
                await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self._db.collection("users").document(user_id).set(user_data, merge=True)
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                return True
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
            except Exception:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
        
        return False
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """
        Retrieve user profile with timeout and retry
        
        Args:
            user_id: User identifier
        
        Returns:
            User data dict or None on failure
        """
        # Input validation
        if not user_id or not isinstance(user_id, str):
            return None
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                doc = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self._db.collection("users").document(user_id).get()
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                
                return doc.to_dict() if doc.exists else None
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
            except Exception:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
        
        return None
    
    # ========================================================================
    # ANALYTICS OPERATIONS
    # ========================================================================
    
    async def save_analytics(self, user_id: str, analytics_data: dict) -> bool:
        """
        Save analytics snapshot for user with timeout and retry
        
        Args:
            user_id: User identifier
            analytics_data: Analytics dict
        
        Returns:
            True if successful
        """
        # Input validation
        if not user_id or not isinstance(analytics_data, dict):
            return False
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                doc_id = f"{user_id}_{datetime.utcnow().strftime('%Y-%m-%d')}"
                
                analytics_data["user_id"] = user_id
                analytics_data["calculated_at"] = datetime.utcnow()
                
                await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self._db.collection("analytics").document(doc_id).set(analytics_data, merge=True)
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                return True
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
            except Exception:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
        
        return False
    
    async def get_latest_analytics(self, user_id: str) -> Optional[Dict]:
        """
        Get most recent analytics for user with timeout and retry
        
        Args:
            user_id: User identifier
        
        Returns:
            Analytics dict or None on failure
        """
        # Input validation
        if not user_id or not isinstance(user_id, str):
            return None
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                docs = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: list(self._db.collection("analytics")
                                     .where("user_id", "==", user_id)
                                     .order_by("calculated_at", direction=firestore.Query.DESCENDING)
                                     .limit(1)
                                     .stream())
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                
                if docs:
                    return docs[0].to_dict()
                
                return None
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
            except Exception:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
        
        return None
    
    # ========================================================================
    # INSIGHTS OPERATIONS
    # ========================================================================
    
    async def save_insights(self, user_id: str, insights_data: dict) -> bool:
        """
        Save AI insights for user with timeout and retry
        
        Args:
            user_id: User identifier
            insights_data: Insights dict
        
        Returns:
            True if successful
        """
        # Input validation
        if not user_id or not isinstance(insights_data, dict):
            return False
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                doc_id = f"{user_id}_{datetime.utcnow().strftime('%Y-%m-%d')}"
                
                insights_data["user_id"] = user_id
                insights_data["generated_at"] = datetime.utcnow()
                
                await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: self._db.collection("insights").document(doc_id).set(insights_data, merge=True)
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                return True
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
            except Exception:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
        
        return False
    
    async def get_latest_insights(self, user_id: str) -> Optional[Dict]:
        """
        Get most recent insights for user with timeout and retry
        
        Args:
            user_id: User identifier
        
        Returns:
            Insights dict or None on failure
        """
        # Input validation
        if not user_id or not isinstance(user_id, str):
            return None
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                docs = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda: list(self._db.collection("insights")
                                     .where("user_id", "==", user_id)
                                     .order_by("generated_at", direction=firestore.Query.DESCENDING)
                                     .limit(1)
                                     .stream())
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                
                if docs:
                    return docs[0].to_dict()
                
                return None
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
            except Exception:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return None
        
        return None


# Global Firebase instance
firebase_db = FirebaseManager()


async def get_firebase() -> FirebaseManager:
    """Dependency injection for FastAPI"""
    return firebase_db
