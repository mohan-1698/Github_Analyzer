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
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any
import logging
import os
import asyncio
import json

logger = logging.getLogger("firebase_service")


def serialize_for_firestore(obj: Any) -> Any:
    """
    Recursively convert datetime/date objects to ISO strings and ensure all keys are strings.
    Handles nested dicts and lists. Firestore requires all keys to be non-empty strings.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, dict):
        # Convert all keys to strings and filter out empty keys
        return {
            str(k): serialize_for_firestore(v) 
            for k, v in obj.items() 
            if str(k).strip()  # Skip empty keys
        }
    elif isinstance(obj, list):
        return [serialize_for_firestore(item) for item in obj]
    else:
        return obj

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
            else:
                # Initialize with service account key
                cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
                
                if not os.path.exists(cred_path):
                    raise FileNotFoundError(f"Service account key not found: {cred_path}")
                
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                self._db = firestore.client()
        
        except Exception as e:
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
            return False
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                # Convert datetime to ISO string for Firestore compatibility
                session_clean = serialize_for_firestore(session_data)
                session_clean["created_at"] = datetime.utcnow().isoformat()
                session_clean["expires_at"] = (datetime.utcnow() + timedelta(days=7)).isoformat()
                
                # Capture variables before lambda to avoid closure issues
                sid = str(session_id)
                data = session_clean
                
                await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda s=sid, d=data: self._db.collection("sessions").document(s).set(d)
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                return True
            
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1)
                    continue
                return False
            except Exception as e:
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
            return None
        
        try:
            # Capture variable before lambda to avoid closure issues
            sid = str(session_id)
            
            doc = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda s=sid: self._db.collection("sessions").document(s).get()
                ),
                timeout=FIREBASE_TIMEOUT
            )
            
            if doc.exists:
                return doc.to_dict()
            return None
        
        except asyncio.TimeoutError:
            return None
        except Exception as e:
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
                # Convert datetime to ISO string for Firestore compatibility
                updates_clean = serialize_for_firestore(updates)
                updates_clean["updated_at"] = datetime.utcnow().isoformat()
                
                # Capture variables before lambda to avoid closure issues
                sid = str(session_id)
                data = updates_clean
                
                await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda s=sid, d=data: self._db.collection("sessions").document(s).update(d)
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
                pass
            
            return count
        
        except Exception as e:
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
                # Convert datetime to ISO string for Firestore compatibility
                user_clean = serialize_for_firestore(user_data)
                user_clean["updated_at"] = datetime.utcnow().isoformat()
                
                if not user_clean.get("created_at"):
                    user_clean["created_at"] = datetime.utcnow().isoformat()
                
                # Capture variables before lambda to avoid closure issues
                uid = str(user_id)
                data = user_clean
                
                await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda u=uid, d=data: self._db.collection("users").document(u).set(d, merge=True)
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
                # Capture user_id before lambda to avoid closure issues
                uid = str(user_id)
                
                doc = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda u=uid: self._db.collection("users").document(u).get()
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
        """Save analytics for user inside users collection"""
        if not user_id or not isinstance(analytics_data, dict):
            return False
        
        try:
            user_id_str = str(user_id)
            analytics_clean = serialize_for_firestore(analytics_data)
            analytics_clean["calculated_at"] = datetime.utcnow().isoformat()
            
            await asyncio.to_thread(
                lambda uid=user_id_str, data=analytics_clean: self._db.collection("users").document(uid).set(
                    {"analytics": data, "updated_at": datetime.utcnow().isoformat()},
                    merge=True
                )
            )
            return True
            
        except Exception as e:
            return False
    
    async def get_latest_analytics(self, user_id: str) -> Optional[Dict]:
        """
        Get latest analytics for user from users collection
        
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
                # Capture user_id before lambda to avoid closure issues
                uid = str(user_id)
                
                doc = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda u=uid: self._db.collection("users").document(u).get()
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                
                if doc.exists:
                    user_data = doc.to_dict()
                    return user_data.get("analytics")
                
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
        """Save AI insights for user inside users collection"""
        if not user_id or not isinstance(insights_data, dict):
            return False
        
        try:
            user_id_str = str(user_id)
            insights_clean = serialize_for_firestore(insights_data)
            insights_clean["generated_at"] = datetime.utcnow().isoformat()
            
            await asyncio.to_thread(
                lambda uid=user_id_str, data=insights_clean: self._db.collection("users").document(uid).set(
                    {"insights": data, "updated_at": datetime.utcnow().isoformat()},
                    merge=True
                )
            )
            return True
            
        except Exception as e:
            return False
    
    async def get_latest_insights(self, user_id: str) -> Optional[Dict]:
        """
        Get latest insights for user from users collection
        
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
                # Capture user_id before lambda to avoid closure issues
                uid = str(user_id)
                
                doc = await asyncio.wait_for(
                    asyncio.to_thread(
                        lambda u=uid: self._db.collection("users").document(u).get()
                    ),
                    timeout=FIREBASE_TIMEOUT
                )
                
                if doc.exists:
                    user_data = doc.to_dict()
                    return user_data.get("insights")
                
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
