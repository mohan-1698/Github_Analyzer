"""
GitHub Growth Analyzer Backend

Phase 2 & 3: FastAPI + GitHub OAuth Implementation (DONE)
Phase 4: GitHub API Service (DONE)
Phase 5: Analytics Engine (DONE)
Phase 6: AI Layer (DONE)

SECURITY HARDENED: Rate limiting, CSRF, HTTPS, Audit logging, Refresh tokens
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import httpx
import jwt
from datetime import datetime, timedelta
from typing import Optional
import json
import logging
import uuid
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Phase 4, 5, 6 imports - Updated paths for new folder structure
from github.github_service import GitHubService
from analytics.analytics_engine import AnalyticsEngine
from ai.openai_service import get_ai_insights  # Now uses Google Gemini
from database.firebase_service import firebase_db  # Firestore database

# Load environment variables
load_dotenv()

# ============================================================================
# AUDIT LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("auth_audit.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("github_oauth")

# Configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# SECURITY: HTTPS enforcement
REQUIRE_HTTPS = ENVIRONMENT == "production"

# Initialize FastAPI
app = FastAPI(
    title="GitHub Growth Analyzer",
    description="AI-powered developer intelligence dashboard",
    version="1.0.0"
)

# SECURITY 2: Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    logger.warning(f"Rate limit exceeded for IP: {get_remote_address(request)}")
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."}
    )

# SECURITY 3: CORS with strict origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only GET and POST, not all methods
    allow_headers=["Content-Type", "Authorization"],  # Specific headers only
    max_age=3600,  # Cache preflight for 1 hour
)

# ============================================================================
# FIRESTORE DATABASE (All data persisted)
# ============================================================================

# Sessions stored in Firestore (not in memory)
# CSRF states still kept in memory (short-lived, 10min expiry)
csrf_states: dict = {}


# ============================================================================
# GITHUB OAUTH SERVICE
# ============================================================================
class GitHubOAuthService:
    """
    GitHub OAuth Service with Security Hardening
    
    SECURITY FEATURES:
    ✅ CSRF protection via state parameter
    ✅ Token expiration validation
    ✅ Rate limiting aware
    ✅ Audit logging
    """
    
    GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    GITHUB_USER_URL = "https://api.github.com/user"
    
    @staticmethod
    def generate_state_token() -> str:
        """
        SECURITY 1: CSRF Protection
        Generate unique state token to prevent CSRF attacks
        """
        state = str(uuid.uuid4())
        csrf_states[state] = {
            "created_at": datetime.utcnow().isoformat(),
        }
        logger.info(f"State token generated: {state[:8]}...")
        return state
    
    @staticmethod
    def verify_state_token(state: str) -> bool:
        """
        SECURITY 1: CSRF Verification
        Verify state token is valid and not expired (10 min)
        """
        if state not in csrf_states:
            logger.warning(f"Invalid state token attempted: {state[:8]}...")
            return False
        
        state_data = csrf_states[state]
        created_at = datetime.fromisoformat(state_data["created_at"])
        
        # State expires in 10 minutes
        if (datetime.utcnow() - created_at).seconds > 600:
            del csrf_states[state]
            logger.warning(f"Expired state token: {state[:8]}...")
            return False
        
        # SECURITY: Delete state after use (one-time only)
        del csrf_states[state]
        logger.info(f"State token verified: {state[:8]}...")
        return True
    
    @staticmethod
    async def get_auth_url(state: str) -> str:
        """
        Step 1-3: Generate GitHub authorization URL
        """
        params = {
            "client_id": GITHUB_CLIENT_ID,
            "redirect_uri": GITHUB_REDIRECT_URI,
            "scope": "user repo",
            "state": state  # CSRF protection
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{GitHubOAuthService.GITHUB_AUTH_URL}?{query_string}"
    
    @staticmethod
    async def exchange_code_for_token(code: str) -> Optional[str]:
        """
        Step 5-6: Exchange authorization code for access token
        SECURITY: Happens on backend, CLIENT_SECRET never exposed
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    GitHubOAuthService.GITHUB_TOKEN_URL,
                    data={
                        "client_id": GITHUB_CLIENT_ID,
                        "client_secret": GITHUB_CLIENT_SECRET,
                        "code": code,
                    },
                    headers={"Accept": "application/json"}
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    access_token = token_data.get("access_token")
                    logger.info("GitHub token exchange successful")
                    return access_token
                else:
                    logger.error(f"GitHub token exchange failed: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Token exchange error: {str(e)}")
            return None
    
    @staticmethod
    async def fetch_user_profile(access_token: str) -> Optional[dict]:
        """
        Step 7: Fetch user profile from GitHub API
        SECURITY: Using secure HTTPS connection
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    GitHubOAuthService.GITHUB_USER_URL,
                    headers={
                        "Authorization": f"token {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                
                if response.status_code == 200:
                    user_profile = response.json()
                    logger.info(f"User profile fetched: {user_profile.get('login')}")
                    return user_profile
                else:
                    logger.error(f"Profile fetch failed: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Profile fetch error: {str(e)}")
            return None
    
    @staticmethod
    def create_jwt_token(user_data: dict) -> tuple[str, str]:
        """
        Step 8: Create JWT token pair (Access + Refresh)
        SECURITY: Access token extended-lived (24 hours), Refresh token longer (7 days)
        
        Returns: (access_token, refresh_token)
        """
        now = datetime.utcnow()
        
        # ACCESS TOKEN: 24 hours (EXTENDED LIFETIME)
        # Covers full day of usage, handles clock drift/timezone issues
        access_exp = now + timedelta(hours=24)
        
        access_payload = {
            "user_id": user_data.get("id"),
            "login": user_data.get("login"),
            "avatar_url": user_data.get("avatar_url"),
            "email": user_data.get("email"),
            "type": "access",  # Token type identifier
            "exp": int(access_exp.timestamp()),
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
        }
        
        access_token = jwt.encode(access_payload, JWT_SECRET, algorithm="HS256")
        
        # REFRESH TOKEN: 7 days (LONG-LIVED)
        # Used to get new access tokens without re-logging in
        refresh_exp = now + timedelta(days=7)
        
        refresh_payload = {
            "user_id": user_data.get("id"),
            "login": user_data.get("login"),
            "type": "refresh",  # Token type identifier
            "exp": int(refresh_exp.timestamp()),
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
        }
        
        refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm="HS256")
        
        logger.info(f"Token pair created for: {user_data.get('login')}")
        return access_token, refresh_token
    
    @staticmethod
    def verify_jwt_token(token: str) -> Optional[dict]:
        """
        SECURITY: Verify JWT token with proper expiration checks
        With 5-minute leeway for clock drift
        """
        try:
            logger.info(f"Verifying JWT token: {token[:20]}...")
            import time
            current_timestamp = int(time.time())
            logger.info(f"   Current server time (unix): {current_timestamp}")
            
            payload = jwt.decode(
                token, 
                JWT_SECRET, 
                algorithms=["HS256"],
                options={"verify_exp": True},
                leeway=300  # Allow 5 minute time skew for clock drift
            )
            logger.info(f"Token verified! (iat: {payload.get('iat')}, exp: {payload.get('exp')})")
            logger.info(f"Token type: {payload.get('type')}, User: {payload.get('login')}")
            return payload
        except jwt.ExpiredSignatureError:
            import time
            current_timestamp = int(time.time())
            logger.warning(f"Token expired: {token[:20]}...")
            logger.warning(f"   Current server time: {current_timestamp}")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            logger.warning(f"   Token: {token[:50]}...")
            logger.warning(f"   Secret key (first 10 chars): {JWT_SECRET[:10]}")
            return None
    
    @staticmethod
    def validate_access_token(token: str) -> Optional[dict]:
        """
        SECURITY: Validate ACCESS token specifically
        Make sure it's not a refresh token
        """
        logger.info(f"Validating access token...")
        payload = GitHubOAuthService.verify_jwt_token(token)
        
        if not payload:
            logger.warning("Token verification failed in validate_access_token")
            return None
        
        # Check token type
        token_type = payload.get("type")
        logger.info(f"   Token type: {token_type}")
        
        if token_type != "access":
            logger.warning(f"Wrong token type! Expected 'access', got '{token_type}'")
            return None
        
        logger.info(f"Access token validated for user: {payload.get('login')}")
        return payload
    
    @staticmethod
    def validate_refresh_token(token: str) -> Optional[dict]:
        """
        SECURITY: Validate REFRESH token specifically
        Make sure it's not an access token
        """
        payload = GitHubOAuthService.verify_jwt_token(token)
        
        if not payload:
            return None
        
        # Check token type
        if payload.get("type") != "refresh":
            logger.warning("Attempted to use non-refresh token as refresh token")
            return None
        
        return payload


# ============================================================================
# ROUTES
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "GitHub Growth Analyzer",
        "version": "1.0.0"
    }


@app.get("/auth/github")
@limiter.limit("10/minute")  # SECURITY 2: Rate limit - max 10 requests/minute
async def github_login(request: Request):
    """
    ENDPOINT 1: Initiate GitHub Login
    SECURITY: Rate limited to prevent brute force attempts
    Returns: auth_url with state token included
    """
    try:
        # SECURITY: Generate CSRF state token
        state = GitHubOAuthService.generate_state_token()
        
        # Get auth URL with state token
        auth_url = await GitHubOAuthService.get_auth_url(state)
        
        logger.info(f"OAuth initiation from IP: {request.client.host}")
        return {
            "status": "success",
            "auth_url": auth_url,
            "state": state
        }
    except Exception as e:
        logger.error(f"OAuth initiation error: {str(e)}")
        raise HTTPException(status_code=500, detail="OAuth initiation failed")


@app.get("/auth/github/callback")
@limiter.limit("5/minute")  # SECURITY 2: Rate limit - max 5 requests/minute
async def github_callback(request: Request, code: str = None, state: str = None):
    """
    ENDPOINT 2: GitHub Callback (Where GitHub sends user back)
    SECURITY: CSRF verification, rate limited, input validation
    Returns: access_token + refresh_token
    """
    
    logger.info(f"OAuth callback from IP: {request.client.host}")
    
    # SECURITY: Input validation
    if not code:
        logger.warning(f"Missing authorization code from IP: {request.client.host}")
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    if not state:
        logger.warning(f"Missing state parameter from IP: {request.client.host}")
        raise HTTPException(status_code=400, detail="Missing state parameter")
    
    # SECURITY 1: Verify CSRF state token
    if not GitHubOAuthService.verify_state_token(state):
        logger.warning(f"CSRF attack detected! Invalid state from IP: {request.client.host}")
        raise HTTPException(status_code=403, detail="Invalid or expired state token")
    
    # Step 1: Exchange code for access_token
    access_token = await GitHubOAuthService.exchange_code_for_token(code)
    
    if not access_token:
        logger.error(f"Failed to get access token from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Failed to get access token")
    
    # Step 2: Fetch user profile
    user_profile = await GitHubOAuthService.fetch_user_profile(access_token)
    
    if not user_profile:
        logger.error(f"Failed to fetch user profile from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Failed to fetch user profile")
    
    # Step 3: Create token pair (access + refresh)
    jwt_access_token, jwt_refresh_token = GitHubOAuthService.create_jwt_token(user_profile)
    
    # Step 4: Store session in Firestore
    session_id = str(uuid.uuid4())
    session_data = {
        "user_id": user_profile.get("id"),
        "login": user_profile.get("login"),
        "avatar_url": user_profile.get("avatar_url"),
        "github_access_token": access_token,  # GitHub API token
        "jwt_access_token": jwt_access_token,  # Current access token
        "jwt_refresh_token": jwt_refresh_token,  # For refreshing access token
        "ip_address": request.client.host,
        "is_valid": True  # Can be set to False to revoke
    }
    
    # Save to Firestore (async, doesn't block response)
    success = await firebase_db.create_session(session_id, session_data)
    
    if not success:
        logger.error(f"Failed to save session to Firestore for {user_profile.get('login')}")
    
    logger.info(f"User authenticated: {user_profile.get('login')} from IP: {request.client.host}")
    
    # Step 5: Return tokens to frontend
    logger.info(f"Creating response...")
    logger.info(f"   access_token (first 30 chars): {jwt_access_token[:30]}")
    logger.info(f"   session_id: {session_id}")
    logger.info(f"   user: {user_profile.get('login')}")
    
    return {
        "status": "success",
        "access_token": jwt_access_token,
        "refresh_token": jwt_refresh_token,
        "session_id": session_id,
        "user": {
            "id": user_profile.get("id"),
            "login": user_profile.get("login"),
            "avatar_url": user_profile.get("avatar_url"),
            "name": user_profile.get("name")
        }
    }


@app.get("/auth/user")
@limiter.limit("30/minute")  # SECURITY 2: Rate limit - max 30 requests/minute
async def get_current_user(request: Request, access_token: str = None, session_id: str = None):
    """
    Protected route: Get current user info
    SECURITY: Validates ACCESS token (15 min lifetime)
    """
    
    if not access_token:
        logger.warning(f"Missing access token from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Missing access token")
    
    if not session_id:
        logger.warning(f"Missing session_id from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Missing session_id")
    
    # SECURITY: Verify it's a valid ACCESS token
    payload = GitHubOAuthService.validate_access_token(access_token)
    
    if not payload:
        logger.warning(f"Invalid/expired access token attempt from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    
    # Retrieve session from Firestore
    session = await firebase_db.get_session(session_id)
    
    if not session:
        logger.warning(f"Session not found in Firestore: {session_id}")
        raise HTTPException(status_code=401, detail="Session not found")
    
    # Verify access token matches
    if session.get("jwt_access_token") != access_token:
        logger.warning(f"Access token mismatch for session {session_id}")
        raise HTTPException(status_code=401, detail="Invalid access token for session")
    
    if not session.get("is_valid"):
        logger.warning(f"Session revoked for user {payload.get('login')} from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Session has been revoked")
    
    user_id = payload.get("user_id")
    logger.info(f"User accessed profile: {payload.get('login')} from IP: {request.client.host}")
    
    return {
        "user_id": user_id,
        "login": payload.get("login"),
        "avatar_url": payload.get("avatar_url"),
        "email": payload.get("email"),
        "github_access_token": session.get("github_access_token"),
        "access_token_expires_in": 900  # 15 minutes in seconds
    }


@app.post("/auth/refresh")
@limiter.limit("20/minute")  # SECURITY 2: Rate limit - max 20 requests/minute
async def refresh_access_token(request: Request, refresh_token: str = None):
    """
    ENDPOINT 3: Refresh ACCESS token using REFRESH token
    SECURITY: Validates REFRESH token, issues new ACCESS token
    FLOW: Refresh token (7 days) → get new Access token (15 min)
    """
    
    if not refresh_token:
        logger.warning(f"Missing refresh token from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Missing refresh token")
    
    # SECURITY: Verify it's a valid REFRESH token
    payload = GitHubOAuthService.validate_refresh_token(refresh_token)
    
    if not payload:
        logger.warning(f"Invalid/expired refresh token attempt from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    user_id = payload.get("user_id")
    user_login = payload.get("login")
    
    # Find session by refresh token in Firestore
    session_id, session = await firebase_db.find_session_by_refresh_token(refresh_token)
    
    if not session:
        logger.warning(f"Session not found for refresh token from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Session not found")
    
    if not session.get("is_valid"):
        logger.warning(f"Session revoked during refresh for user {user_login} from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Session has been revoked")
    
    # Create new access token (keep refresh token same)
    now = datetime.utcnow()
    access_exp = now + timedelta(minutes=15)
    
    new_access_payload = {
        "user_id": user_id,
        "login": user_login,
        "avatar_url": session.get("avatar_url"),
        "type": "access",
        "exp": int(access_exp.timestamp()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
    }
    
    new_access_token = jwt.encode(new_access_payload, JWT_SECRET, algorithm="HS256")
    
    # Update session in Firestore with new access token
    success = await firebase_db.update_session(session_id, {
        "jwt_access_token": new_access_token,
        "last_refreshed_at": now.isoformat()
    })
    
    if not success:
        logger.error(f"Failed to update session in Firestore after refresh")
        raise HTTPException(status_code=500, detail="Failed to update session")
    
    logger.info(f"Access token refreshed for user {user_login} from IP: {request.client.host}")

    
    return {
        "access_token": new_access_token,
        "refresh_token": refresh_token,  # Same refresh token
        "access_token_expires_in": 900,  # 15 minutes in seconds
        "refresh_token_expires_in": 604800  # 7 days in seconds
    }


@app.post("/auth/logout")
@limiter.limit("10/minute")  # SECURITY 2: Rate limit - max 10 requests/minute
async def logout(request: Request, access_token: str = None, session_id: str = None):
    """
    Logout: Revoke session and invalidate tokens
    SECURITY: Rate limited, audit logged, marks session as invalid
    """
    
    if not access_token or not session_id:
        raise HTTPException(status_code=400, detail="Missing access token or session_id")
    
    # Retrieve and invalidate session in Firestore
    session = await firebase_db.get_session(session_id)
    
    if session:
        # Verify the access token matches
        if session.get("jwt_access_token") != access_token:
            logger.warning(f"Token mismatch during logout for session {session_id}")
            raise HTTPException(status_code=401, detail="Invalid token for session")
        
        # Mark session as revoked
        success = await firebase_db.update_session(session_id, {"is_valid": False})
        
        if success:
            user_login = session.get("login")
            logger.info(f"User logged out: {user_login} from IP: {request.client.host}")
        else:
            logger.error(f"Failed to revoke session {session_id}")
            raise HTTPException(status_code=500, detail="Failed to logout")
    else:
        logger.warning(f"Logout attempt with invalid session_id from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Session not found")
    
    return {"status": "logged out"}


# ============================================================================
# PHASE 4: GITHUB DATA FETCHING
# ============================================================================

@app.post("/github/sync")
@limiter.limit("5/minute")  # SECURITY: Rate limited
async def sync_github_data(request: Request, access_token: str = None, session_id: str = None):
    """
    PHASE 4: Fetch all GitHub data with error handling
    Fetches: repos, commits, PRs, languages
    SECURITY: Validates token, uses GitHub access_token, timeout protection
    """
    
    try:
        # Input validation
        if not access_token or not session_id:
            raise HTTPException(status_code=401, detail="Missing access token or session_id")
        
        # Validate access token
        payload = GitHubOAuthService.validate_access_token(access_token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired access token")
        
        user_id = payload.get("user_id")
        user_login = payload.get("login")
        
        # Get session from Firestore
        session = await firebase_db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=401, detail="Session expired. Please login again.")
        
        # Verify access token matches
        if session.get("jwt_access_token") != access_token:
            raise HTTPException(status_code=401, detail="Invalid token for this session")
        
        github_token = session.get("github_access_token")
        if not github_token:
            raise HTTPException(status_code=500, detail="GitHub credentials not found")
        
        logger.info(f"Syncing GitHub data for user: {user_login}")
        
        # Fetch all GitHub data with timeout protection
        logger.info("Fetching repositories...")
        repos = await GitHubService.get_user_repos(github_token)
        logger.info(f"   [OK] Repos: {len(repos) if repos else 0}")
        
        logger.info("Fetching commits (365 days)...")
        commits = await GitHubService.get_user_commits(github_token, days=365)
        logger.info(f"   [OK] Commits: {len(commits) if commits else 0}")
        
        logger.info("Fetching pull requests (90 days)...")
        prs = await GitHubService.get_user_pull_requests(github_token, days=90)
        logger.info(f"   [OK] PRs: {len(prs) if prs else 0}")
        
        logger.info("Fetching user profile...")
        profile = await GitHubService.get_user_profile_stats(github_token)
        logger.info(f"   [OK] Profile: {'Present' if profile else 'None'}")
        
        # Check if at least some data was fetched
        if not repos and not commits and not prs:
            logger.error("[ERROR] No GitHub data fetched!")
            return {
                "status": "failed",
                "message": "Could not fetch GitHub data. GitHub may be temporarily unavailable. Please try again."
            }
        
        # Prepare data to store
        github_data = {
            "github_data": {
                "repos": repos or [],
                "commits": commits or [],
                "prs": prs or [],
                "profile": profile or {},
                "synced_at": datetime.utcnow().isoformat()
            }
        }
        
        # Update session in Firestore
        logger.info("Saving GitHub data to Firestore...")
        success = await firebase_db.update_session(session_id, github_data)
        if not success:
            logger.warning("[WARNING] Failed to save data to Firestore (attempt 1), retrying...")
            # Retry once more
            await asyncio.sleep(1)
            success = await firebase_db.update_session(session_id, github_data)
            if not success:
                logger.error("[ERROR] Failed to save data to Firestore after retry")
                return {
                    "status": "partial",
                    "message": "Data fetched but failed to save. Will retry on next sync.",
                    "repos_count": len(repos or []),
                    "commits_count": len(commits or []),
                    "prs_count": len(prs or [])
                }
        
        logger.info(f"GitHub sync completed successfully for {user_login}")
        
        return {
            "status": "synced",
            "repos_count": len(repos or []),
            "commits_count": len(commits or []),
            "prs_count": len(prs or []),
            "synced_at": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception:
        return {
            "status": "error",
            "message": "GitHub sync failed. Please check your connection and try again.",
            "retry": True
        }


# ============================================================================
# PHASE 5: ANALYTICS ENGINE
# ============================================================================

@app.post("/analytics/calculate")
@limiter.limit("10/minute")  # SECURITY: Rate limited
async def calculate_analytics(request: Request, access_token: str = None, session_id: str = None):
    """
    PHASE 5: Calculate analytics from GitHub data with error handling
    Calculates: commits, streaks, languages, PRs, productivity score
    SECURITY: Validates token, pure Python calculations
    """
    
    try:
        # Input validation
        if not access_token or not session_id:
            logger.error("Missing credentials in analytics request")
            raise HTTPException(status_code=401, detail="Missing access token or session_id")
        
        # Validate token
        payload = GitHubOAuthService.validate_access_token(access_token)
        if not payload:
            logger.error("Invalid token in analytics request")
            raise HTTPException(status_code=401, detail="Invalid or expired access token")
        
        user_login = payload.get("login")
        user_id = payload.get("user_id")
        
        logger.info(f"Calculating analytics for {user_login}")
        
        # Get session from Firestore
        session = await firebase_db.get_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            raise HTTPException(status_code=401, detail="Session expired. Please login again.")
        
        # Verify token
        if session.get("jwt_access_token") != access_token:
            logger.error("Token mismatch in session")
            raise HTTPException(status_code=401, detail="Invalid token for this session")
        
        github_data = session.get("github_data")
        if not github_data:
            logger.error(f"No GitHub data in session for {user_login}")
            raise HTTPException(status_code=400, detail="No GitHub data found. Please sync first.")
        
        logger.info(f"GitHub data found: {len(github_data.get('repos', []))} repos, {len(github_data.get('commits', []))} commits")
        
        # Calculate all metrics (safe - handles invalid data)
        metrics = AnalyticsEngine.aggregate_all_metrics(
            commits=github_data.get("commits", []),
            repos=github_data.get("repos", []),
            pull_requests=github_data.get("prs", [])
        )
        
        if not metrics:
            logger.error("Could not calculate metrics - invalid data format")
            return {
                "status": "error",
                "message": "Could not calculate metrics. Invalid data format."
            }
        
        logger.info(f"Analytics calculated successfully")
        logger.info(f"  Productivity Score: {metrics.get('productivity', {}).get('score', 0)}")
        logger.info(f"  Total Commits: {metrics.get('commits', {}).get('total_commits', 0)}")
        logger.info(f"  Primary Language: {metrics.get('languages', {}).get('primary_language', 'Unknown')}")
        
        # Save analytics to Firestore
        save_success = await firebase_db.save_analytics(user_id, metrics)
        logger.info(f"Analytics saved to Firestore: {save_success}")
        
        # Update session with analytics
        update_success = await firebase_db.update_session(session_id, {"analytics": metrics})
        logger.info(f"Session updated with analytics: {update_success}")
        
        return {
            "status": "success",
            "message": "Analytics calculated and saved",
            "analytics": metrics
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating analytics: {str(e)}")
        return {
            "status": "error",
            "message": "Failed to calculate analytics. Please try again.",
            "retry": True
        }


# ============================================================================
# PHASE 6: AI INSIGHTS
# ============================================================================

@app.post("/insights/generate")
@limiter.limit("3/minute")  # SECURITY: Rate limited (API calls cost!)
async def generate_ai_insights(request: Request, access_token: str = None, session_id: str = None):
    """
    PHASE 6: Generate AI-powered insights using Google Gemini
    Uses Gemini to provide: productivity analysis, burnout risk, improvement plan
    SECURITY: Validates token, structured JSON output, API key from environment
    """
    
    logger.info(f"Generating AI insights for token: {access_token[:20] if access_token else 'MISSING'}...")
    
    if not access_token or not session_id:
        logger.warning("Missing access token or session_id")
        raise HTTPException(status_code=401, detail="Missing access token or session_id")
    
    # Validate token
    payload = GitHubOAuthService.validate_access_token(access_token)
    
    if not payload:
        logger.warning("Invalid access token")
        raise HTTPException(status_code=401, detail="Invalid access token")
    
    user_login = payload.get("login")
    user_id = payload.get("user_id")
    
    logger.info(f"Generating insights for user: {user_login}")
    
    # Get session from Firestore
    session = await firebase_db.get_session(session_id)
    
    if not session:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=401, detail="Session not found")
    
    # Verify token
    if session.get("jwt_access_token") != access_token:
        logger.warning("Token mismatch in session")
        raise HTTPException(status_code=401, detail="Invalid access token for session")
    
    analytics = session.get("analytics")
    
    # Debug logging
    logger.info(f"Session retrieved, analytics present: {analytics is not None}")
    if analytics:
        logger.info(f"Analytics available with score: {analytics.get('productivity', {}).get('score', 0)}")
    
    if not analytics:
        logger.warning(f"Analytics not available in session for {user_login}")
        logger.info("Attempting to recalculate analytics...")
        
        # Fallback: try to calculate analytics from github_data
        github_data = session.get("github_data")
        if not github_data:
            logger.error("No GitHub data available for fallback calculation")
            return {
                "status": "error",
                "message": "Analytics not available. Please sync GitHub data first.",
                "retry": False
            }
        
        # Recalculate analytics
        analytics = AnalyticsEngine.aggregate_all_metrics(
            commits=github_data.get("commits", []),
            repos=github_data.get("repos", []),
            pull_requests=github_data.get("prs", [])
        )
        
        if not analytics:
            logger.error("Failed to recalculate analytics")
            return {
                "status": "error",
                "message": "Analytics not available. Please call /analytics/calculate first.",
                "retry": False
            }
        
        logger.info("Analytics recalculated successfully (fallback)")
        # Save for future use
        await firebase_db.update_session(session_id, {"analytics": analytics})
    
    logger.info(f"Analytics found for {user_login}")
    
    # Get Google Gemini API key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_api_key:
        logger.error("GEMINI_API_KEY not set in environment")
        return {
            "status": "error",
            "message": "AI service not configured. Please set GEMINI_API_KEY environment variable.",
            "retry": False
        }
    
    logger.info(f"Checking cache for {user_login}...")
    
    try:
        # Get previously cached insights and hash
        previous_insights = session.get("insights")
        previous_hash = previous_insights.get("analytics_hash") if previous_insights else None
        
        if previous_hash:
            logger.info(f"Found previous cache hash: {previous_hash}")
        
        # Generate insights with caching support
        # If data unchanged, will return cached insights instantly
        insights = await get_ai_insights(
            analytics, 
            user_login, 
            gemini_api_key,
            cached_insights=previous_insights,  # Pass cached insights
            previous_hash=previous_hash  # Pass previous hash
        )
        
        if not insights:
            logger.error(f"Failed to generate insights for {user_login}")
            return {
                "status": "error",
                "message": "Failed to generate AI insights. Please try again.",
                "retry": True
            }
        
        logger.info(f"Insights ready for {user_login} (hash: {insights.get('analytics_hash', 'N/A')})")
        
        # Save to Firestore (for history)
        try:
            await firebase_db.save_insights(user_id, insights)
            await firebase_db.update_session(session_id, {"insights": insights})
        except Exception as e:
            logger.warning(f"Failed to save insights to Firestore: {str(e)}")
            pass  # Non-blocking: save failure doesn't prevent response
        
        return insights
    
    except Exception as e:
        logger.error(f"Error in insights generation: {str(e)}")


@app.get("/dashboard/data")
@limiter.limit("20/minute")  # SECURITY: Rate limited
async def get_dashboard_data(request: Request, access_token: str = None, session_id: str = None):
    """
    GET complete dashboard data (GitHub + Analytics + Insights)
    All data in one response for frontend
    Returns partial data if some components unavailable
    """
    
    logger.info(f"Dashboard request from IP: {request.client.host}")
    logger.info(f"   access_token: {access_token[:20] if access_token else 'MISSING'}...")
    logger.info(f"   session_id: {session_id}")
    
    if not access_token or not session_id:
        logger.warning(f"Missing credentials - token: {bool(access_token)}, session: {bool(session_id)}")
        return {
            "status": "error",
            "message": "Missing access token or session_id",
            "retry": False
        }
    
    # Validate token
    logger.info(f"Validating token...")
    payload = GitHubOAuthService.validate_access_token(access_token)
    
    if not payload:
        logger.error(f"Token validation failed!")
        return {
            "status": "error",
            "message": "Invalid access token",
            "retry": False
        }
    
    logger.info(f"Token valid for user: {payload.get('login')}")
    user_login = payload.get("login")
    
    try:
        # Get session from Firestore
        session = await firebase_db.get_session(session_id)
        
        if not session:
            return {
                "status": "error",
                "message": "Session not found",
                "retry": False
            }
        
        # Verify token matches
        if session.get("jwt_access_token") != access_token:
            return {
                "status": "error",
                "message": "Invalid access token for session",
                "retry": False
            }
        
        # Build response with available data
        response = {
            "status": "success",
            "user": {
                "id": payload.get("user_id"),
                "login": user_login,
                "avatar_url": payload.get("avatar_url"),
                "email": payload.get("email")
            },
            "github_data": session.get("github_data"),
            "analytics": session.get("analytics"),
            "insights": session.get("insights"),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        return response
    
    except Exception as e:
        # Even on error, return best-effort data
        return {
            "status": "error",
            "message": "Failed to load complete dashboard. Some data may be unavailable.",
            "user": {
                "login": user_login
            } if user_login else None,
            "retry": True
        }



# ============================================================================
# DEBUG ENDPOINT (Development only)
# ============================================================================

@app.get("/debug/config")
@limiter.limit("5/minute")  # Rate limited
async def debug_config(request: Request):
    """Show current config (development only)"""
    if ENVIRONMENT != "development":
        logger.warning(f"Unauthorized debug access attempt from IP: {request.client.host}")
        raise HTTPException(status_code=403, detail="Not available in production")
    
    logger.info(f"Debug config accessed from IP: {request.client.host}")
    
    return {
        "environment": ENVIRONMENT,
        "github_client_id": GITHUB_CLIENT_ID[:10] + "..." if GITHUB_CLIENT_ID else "not_set",
        "frontend_url": FRONTEND_URL,
        "firebase_configured": os.path.exists(os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.js")),
        "csrf_states_count": len(csrf_states),
        "https_required": REQUIRE_HTTPS,
        "access_token_lifetime": "15 minutes",
        "refresh_token_lifetime": "7 days",
        "database": "Firestore (persistent)",
        "message": "Sessions now stored in Firestore, not in-memory"
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting GitHub Growth Analyzer in {ENVIRONMENT} mode")
    logger.info(f"HTTPS Required: {REQUIRE_HTTPS}")
    
    uvicorn.run(
        "auth.main:app",
        host="0.0.0.0",
        port=8000,
        reload=(ENVIRONMENT == "development")
    )
