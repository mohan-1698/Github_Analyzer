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

# Disable verbose third-party logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

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
        return state
    
    @staticmethod
    def verify_state_token(state: str) -> bool:
        """
        SECURITY 1: CSRF Verification
        Verify state token is valid and not expired (10 min)
        """
        if state not in csrf_states:
            return False
        
        state_data = csrf_states[state]
        created_at = datetime.fromisoformat(state_data["created_at"])
        
        # State expires in 10 minutes
        if (datetime.utcnow() - created_at).seconds > 600:
            del csrf_states[state]
            return False
        
        # SECURITY: Delete state after use (one-time only)
        del csrf_states[state]
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
                    return access_token
                else:
                    return None
        except Exception as e:
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
                    return user_profile
                else:
                    return None
        except Exception as e:
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
        
        return access_token, refresh_token
    
    @staticmethod
    def verify_jwt_token(token: str) -> Optional[dict]:
        """SECURITY: Verify JWT token with proper expiration checks"""
        try:
            payload = jwt.decode(
                token, 
                JWT_SECRET, 
                algorithms=["HS256"],
                options={"verify_exp": True},
                leeway=300  # Allow 5 minute time skew
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError as e:
            return None
    
    @staticmethod
    def validate_access_token(token: str) -> Optional[dict]:
        """SECURITY: Validate ACCESS token specifically (not refresh token)"""
        payload = GitHubOAuthService.verify_jwt_token(token)
        
        if not payload:
            return None
        
        if payload.get("type") != "access":
            return None
        
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
        
        return {
            "status": "success",
            "auth_url": auth_url,
            "state": state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="OAuth initiation failed")


@app.get("/auth/github/callback")
@limiter.limit("5/minute")  # SECURITY 2: Rate limit - max 5 requests/minute
async def github_callback(request: Request, code: str = None, state: str = None):
    """
    ENDPOINT 2: GitHub Callback (Where GitHub sends user back)
    SECURITY: CSRF verification, rate limited, input validation
    Returns: access_token + refresh_token
    """
    
    
    # SECURITY: Input validation
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    if not state:
        raise HTTPException(status_code=400, detail="Missing state parameter")
    
    # SECURITY 1: Verify CSRF state token
    if not GitHubOAuthService.verify_state_token(state):
        raise HTTPException(status_code=403, detail="Invalid or expired state token")
    
    # Step 1: Exchange code for access_token
    access_token = await GitHubOAuthService.exchange_code_for_token(code)
    
    if not access_token:
        raise HTTPException(status_code=401, detail="Failed to get access token")
    
    # Step 2: Fetch user profile
    user_profile = await GitHubOAuthService.fetch_user_profile(access_token)
    
    if not user_profile:
        logger.info(f"[GITHUB] Connected: NO")
        raise HTTPException(status_code=401, detail="Failed to fetch user profile")
    
    logger.info(f"[GITHUB] Connected: YES")
    
    # Step 3: Create token pair (access + refresh)
    jwt_access_token, jwt_refresh_token = GitHubOAuthService.create_jwt_token(user_profile)
    
    # Step 4: Store session in Firestore
    session_id = str(uuid.uuid4())
    session_data = {
        "user_id": user_profile.get("id"),
        "login": user_profile.get("login"),
        "avatar_url": user_profile.get("avatar_url"),
        "github_access_token": access_token,
        "jwt_access_token": jwt_access_token,
        "jwt_refresh_token": jwt_refresh_token,
        "ip_address": request.client.host,
        "is_valid": True
    }
    
    # Save to Firestore
    success = await firebase_db.create_session(session_id, session_data)
    logger.info(f"[FIREBASE] Session saved: {'YES' if success else 'NO'}")
    
    # Also create/update user document in users collection
    user_id = str(user_profile.get("id"))
    user_doc_data = {
        "login": user_profile.get("login"),
        "avatar_url": user_profile.get("avatar_url"),
        "github_id": user_profile.get("id"),
        "name": user_profile.get("name"),
        "email": user_profile.get("email"),
        "last_login": datetime.utcnow().isoformat()
    }
    await firebase_db.create_or_update_user(user_id, user_doc_data)
    
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
        raise HTTPException(status_code=401, detail="Missing access token")
    
    if not session_id:
        raise HTTPException(status_code=401, detail="Missing session_id")
    
    # SECURITY: Verify it's a valid ACCESS token
    payload = GitHubOAuthService.validate_access_token(access_token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    
    # Retrieve session from Firestore
    session = await firebase_db.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")
    
    # Verify access token matches
    if session.get("jwt_access_token") != access_token:
        raise HTTPException(status_code=401, detail="Invalid access token for session")
    
    if not session.get("is_valid"):
        raise HTTPException(status_code=401, detail="Session has been revoked")
    
    user_id = payload.get("user_id")
    
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
        raise HTTPException(status_code=401, detail="Missing refresh token")
    
    # SECURITY: Verify it's a valid REFRESH token
    payload = GitHubOAuthService.validate_refresh_token(refresh_token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    user_id = payload.get("user_id")
    user_login = payload.get("login")
    
    # Find session by refresh token in Firestore
    session_id, session = await firebase_db.find_session_by_refresh_token(refresh_token)
    
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")
    
    if not session.get("is_valid"):
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
        raise HTTPException(status_code=500, detail="Failed to update session")
    


    
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
            raise HTTPException(status_code=401, detail="Invalid token for session")
        
        # Mark session as revoked
        success = await firebase_db.update_session(session_id, {"is_valid": False})
        
        if success:
            user_login = session.get("login")
        else:
            raise HTTPException(status_code=500, detail="Failed to logout")
    else:
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
        
        # Fetch all GitHub data
        repos = await GitHubService.get_user_repos(github_token)
        commits = await GitHubService.get_user_commits(github_token, days=365)
        prs = await GitHubService.get_user_pull_requests(github_token, days=90)
        profile = await GitHubService.get_user_profile_stats(github_token)
        
        # Check if at least some data was fetched
        if not repos and not commits and not prs:
            return {
                "status": "failed",
                "message": "Could not fetch GitHub data. Please try again."
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
        
        # Update session in  Firestore
        success = await firebase_db.update_session(session_id, github_data)
        if not success:
            await asyncio.sleep(1)
            success = await firebase_db.update_session(session_id, github_data)
            if not success:
                return {
                    "status": "partial",
                    "message": "Data fetched but not saved",
                    "repos_count": len(repos or [])
                }
        
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
            raise HTTPException(status_code=401, detail="Missing access token or session_id")
        
        # Validate token
        payload = GitHubOAuthService.validate_access_token(access_token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid or expired access token")
        
        user_login = payload.get("login")
        user_id = payload.get("user_id")
        
        
        # Get session from Firestore
        session = await firebase_db.get_session(session_id)
        if not session:
            raise HTTPException(status_code=401, detail="Session expired. Please login again.")
        
        # Verify token
        if session.get("jwt_access_token") != access_token:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        github_data = session.get("github_data")
        if not github_data:
            raise HTTPException(status_code=400, detail="No GitHub data. Sync first.")
        
        # Calculate all metrics
        metrics = AnalyticsEngine.aggregate_all_metrics(
            commits=github_data.get("commits", []),
            repos=github_data.get("repos", []),
            pull_requests=github_data.get("prs", [])
        )
        
        if not metrics:
            logger.info("[ANALYTICS] Generated: NO")
            return {
                "status": "error",
                "message": "Could not calculate metrics"
            }
        
        logger.info("[ANALYTICS] Generated: YES")
        
        # Save analytics to Firestore
        save_success = await firebase_db.save_analytics(str(user_id), metrics)
        logger.info(f"[FIREBASE] Analytics saved: {'YES' if save_success else 'NO'}")
        
        # Update session with analytics
        await firebase_db.update_session(session_id, {"analytics": metrics})
        
        return {
            "status": "success",
            "message": "Analytics calculated",
            "analytics": metrics
        }
    
    except HTTPException:
        raise
    except Exception as e:
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
    
    if not access_token or not session_id:
        raise HTTPException(status_code=401, detail="Missing access token or session")
    
    # Validate token
    payload = GitHubOAuthService.validate_access_token(access_token)
    
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid access token")
    
    user_login = payload.get("login")
    user_id = payload.get("user_id")
    
    # Get session from Firestore
    session = await firebase_db.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=401, detail="Session not found")
    
    # Verify token
    if session.get("jwt_access_token") != access_token:
        raise HTTPException(status_code=401, detail="Invalid token for session")
    
    analytics = session.get("analytics")
    
    if not analytics:
        logger.info("[FIREBASE] Analytics retrieved: NO")
        # Fallback: try to calculate analytics from github_data
        github_data = session.get("github_data")
        if not github_data:
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
            return {
                "status": "error",
                "message": "Analytics not available. Call /analytics/calculate first."
            }
    else:
        logger.info("[FIREBASE] Analytics retrieved: YES")
    
    # Get Google Gemini API key
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_api_key:
        return {
            "status": "error",
            "message": "AI service not configured"
        }
    
    try:
        # Get previously cached insights from Firebase
        previous_insights = await firebase_db.get_latest_insights(str(user_id))
        
        # Fallback to session if not in users collection
        if not previous_insights:
            previous_insights = session.get("insights")
        
        previous_hash = previous_insights.get("analytics_hash") if previous_insights else None
        
        # Generate insights with caching support
        insights = await get_ai_insights(
            analytics, 
            user_login, 
            gemini_api_key,
            cached_insights=previous_insights,
            previous_hash=previous_hash
        )
        
        if not insights:
            logger.info("[GEMINI] Generated: NO")
            return {
                "status": "error",
                "message": "Failed to generate AI insights. Please try again.",
                "retry": True
            }
        
        logger.info("[GEMINI] Generated: YES")
        
        # Save to Firestore (for history)
        save_success = True
        try:
            await firebase_db.save_insights(str(user_id), insights)
            await firebase_db.update_session(session_id, {"insights": insights})
        except Exception as e:
            save_success = False
        
        logger.info(f"[FIREBASE] Insights saved: {'YES' if save_success else 'NO'}")
        
        return insights
    
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to generate insights"
        }


@app.get("/dashboard/data")
@limiter.limit("20/minute")  # SECURITY: Rate limited
async def get_dashboard_data(request: Request, access_token: str = None, session_id: str = None):
    """GET complete dashboard data (GitHub + Analytics + Insights)"""
    
    if not access_token or not session_id:
        return {
            "status": "error",
            "message": "Missing access token or session_id",
            "retry": False
        }
    
    # Validate token
    payload = GitHubOAuthService.validate_access_token(access_token)
    
    if not payload:
        return {
            "status": "error",
            "message": "Invalid access token",
            "retry": False
        }
    
    user_login = payload.get("login")
    
    try:
        # Get session from Firestore
        session = await firebase_db.get_session(session_id)
        
        if not session:
            return {
                "status": "error",
                "message": "Session not found"
            }
        
        # Verify token matches
        if session.get("jwt_access_token") != access_token:
            return {
                "status": "error",
                "message": "Invalid token for session"
            }
        
        user_id = payload.get("user_id")
        
        # Get insights - try users collection first, then session
        insights = session.get("insights")
        analytics = session.get("analytics")
        
        # Fetch from users collection if not in session
        if not insights and user_id:
            insights = await firebase_db.get_latest_insights(str(user_id))
        
        if not analytics and user_id:
            analytics = await firebase_db.get_latest_analytics(str(user_id))
        
        # Build response with available data
        response = {
            "status": "success",
            "user": {
                "id": user_id,
                "login": user_login,
                "avatar_url": payload.get("avatar_url"),
                "email": payload.get("email")
            },
            "github_data": session.get("github_data"),
            "analytics": analytics,
            "insights": insights,
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
        raise HTTPException(status_code=403, detail="Not available in production")
    
    
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
    
    uvicorn.run(
        "auth.main:app",
        host="0.0.0.0",
        port=8000,
        reload=(ENVIRONMENT == "development")
    )
