"""
GitHub Growth Analyzer Backend

Phase 2 & 3: FastAPI + GitHub OAuth Implementation
SECURITY HARDENED: Rate limiting, CSRF, HTTPS, Audit logging
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.https import HTTPSRedirectMiddleware
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

# SECURITY 1: HTTPS Redirect Middleware (Production only)
if REQUIRE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)

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
# IN-MEMORY STORAGE (SECURITY: Will move to database)
# ============================================================================

# Store CSRF state: {state_token -> {user_ip, created_at}}
csrf_states: dict = {}

# Store sessions: {jwt_token -> {user_data, created_at}}
sessions_db: dict = {}


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
        SECURITY: Access token short-lived (15 min), Refresh token longer (7 days)
        
        Returns: (access_token, refresh_token)
        """
        now = datetime.utcnow()
        
        # ACCESS TOKEN: 15 minutes (SHORT-LIVED)
        # If stolen, attacker can only use it for 15 minutes
        access_exp = now + timedelta(minutes=15)
        
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
        """
        try:
            payload = jwt.decode(
                token, 
                JWT_SECRET, 
                algorithms=["HS256"],
                options={"verify_exp": True}  # Verify expiration
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Attempted to use expired token")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token attempted: {str(e)}")
            return None
    
    @staticmethod
    def validate_access_token(token: str) -> Optional[dict]:
        """
        SECURITY: Validate ACCESS token specifically
        Make sure it's not a refresh token
        """
        payload = GitHubOAuthService.verify_jwt_token(token)
        
        if not payload:
            return None
        
        # Check token type
        if payload.get("type") != "access":
            logger.warning("Attempted to use non-access token as access token")
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
    """
    try:
        # SECURITY: Generate CSRF state token
        state = GitHubOAuthService.generate_state_token()
        
        # Get auth URL with state token
        auth_url = await GitHubOAuthService.get_auth_url(state)
        
        logger.info(f"OAuth initiation from IP: {request.client.host}")
        return RedirectResponse(url=auth_url)
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
    
    # Step 4: Store session with both tokens
    session_id = str(uuid.uuid4())
    sessions_db[session_id] = {
        "user_id": user_profile.get("id"),
        "login": user_profile.get("login"),
        "avatar_url": user_profile.get("avatar_url"),
        "github_access_token": access_token,  # GitHub API token
        "jwt_access_token": jwt_access_token,  # Current access token
        "jwt_refresh_token": jwt_refresh_token,  # For refreshing access token
        "created_at": datetime.utcnow().isoformat(),
        "ip_address": request.client.host,
        "is_valid": True  # Can be set to False to revoke
    }
    
    logger.info(f"User authenticated: {user_profile.get('login')} from IP: {request.client.host}")
    
    # Step 5: Redirect to frontend with both tokens
    # In frontend: extract tokens from URL, store them securely
    params = f"?access_token={jwt_access_token}&refresh_token={jwt_refresh_token}"
    frontend_redirect = f"{FRONTEND_URL}/auth/success{params}"
    return RedirectResponse(url=frontend_redirect)


@app.get("/auth/user")
@limiter.limit("30/minute")  # SECURITY 2: Rate limit - max 30 requests/minute
async def get_current_user(request: Request, access_token: str = None):
    """
    Protected route: Get current user info
    SECURITY: Validates ACCESS token (15 min lifetime)
    """
    
    if not access_token:
        logger.warning(f"Missing access token from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Missing access token")
    
    # SECURITY: Verify it's a valid ACCESS token
    payload = GitHubOAuthService.validate_access_token(access_token)
    
    if not payload:
        logger.warning(f"Invalid/expired access token attempt from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    
    user_id = payload.get("user_id")
    
    # Find session by access token
    session = None
    for session_data in sessions_db.values():
        if session_data.get("jwt_access_token") == access_token:
            session = session_data
            break
    
    if not session:
        logger.warning(f"Session not found for valid token from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Session not found")
    
    if not session.get("is_valid"):
        logger.warning(f"Session revoked for user {payload.get('login')} from IP: {request.client.host}")
        raise HTTPException(status_code=401, detail="Session has been revoked")
    
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
    
    # Find session by refresh token
    session_id = None
    session = None
    
    for sid, session_data in sessions_db.items():
        if session_data.get("jwt_refresh_token") == refresh_token:
            session_id = sid
            session = session_data
            break
    
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
    
    # Update session with new access token
    session["jwt_access_token"] = new_access_token
    session["last_refreshed_at"] = now.isoformat()
    
    logger.info(f"Access token refreshed for user {user_login} from IP: {request.client.host}")
    
    return {
        "access_token": new_access_token,
        "refresh_token": refresh_token,  # Same refresh token
        "access_token_expires_in": 900,  # 15 minutes in seconds
        "refresh_token_expires_in": 604800  # 7 days in seconds
    }


@app.post("/auth/logout")
@limiter.limit("10/minute")  # SECURITY 2: Rate limit - max 10 requests/minute
async def logout(request: Request, access_token: str = None):
    """
    Logout: Revoke session and invalidate tokens
    SECURITY: Rate limited, audit logged, marks session as invalid
    """
    
    if not access_token:
        raise HTTPException(status_code=400, detail="Missing access token")
    
    # Find and invalidate session
    session_id = None
    session = None
    
    for sid, session_data in sessions_db.items():
        if session_data.get("jwt_access_token") == access_token:
            session_id = sid
            session = session_data
            break
    
    if session:
        user_login = session.get("login")
        session["is_valid"] = False  # Mark as revoked
        logger.info(f"User logged out: {user_login} from IP: {request.client.host}")
    else:
        logger.warning(f"Logout attempt with invalid token from IP: {request.client.host}")
    
    return {"status": "logged out"}


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
    
    # Count active sessions
    active_sessions = sum(1 for s in sessions_db.values() if s.get("is_valid"))
    revoked_sessions = sum(1 for s in sessions_db.values() if not s.get("is_valid"))
    
    return {
        "environment": ENVIRONMENT,
        "github_client_id": GITHUB_CLIENT_ID[:10] + "..." if GITHUB_CLIENT_ID else "not_set",
        "frontend_url": FRONTEND_URL,
        "active_sessions": active_sessions,
        "revoked_sessions": revoked_sessions,
        "csrf_states_count": len(csrf_states),
        "https_required": REQUIRE_HTTPS,
        "access_token_lifetime": "15 minutes",
        "refresh_token_lifetime": "7 days"
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting GitHub Growth Analyzer in {ENVIRONMENT} mode")
    logger.info(f"HTTPS Required: {REQUIRE_HTTPS}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=(ENVIRONMENT == "development")
    )
