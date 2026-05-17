from fastapi import Request, Depends, HTTPException
from fastapi.responses import Response, RedirectResponse
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
import jwt as PyJWT
from config import settings
from database import get_db
import models
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Public paths that don't need authentication
PUBLIC_PATHS = {
    "/login",
    "/register", 
    "/api/auth/login",
    "/api/auth/register",
    "/static",
    "/health",
    "/favicon.ico"
}

# Admin-only paths - MUST include all possible admin paths
ADMIN_PATHS = {
    "/admin",          # Base admin path
    "/admin/debug",    # Debug center 
    "/users",         # User management
    "/audit",         # Audit logs
    "/api/admin"      # Admin API endpoints
}

# ESP32 endpoints that use API key
ESP32_PATHS = {
    "/api/system-mode",
    "/api/workflow/progress"
}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        logger.debug("Processing request to: %s", path)
        
        # Check if path is public
        is_public = any(path == p or path.startswith(p + '/') for p in PUBLIC_PATHS)
        
        # Check if it's an ESP32 endpoint
        is_esp32_endpoint = any(path == p or path.startswith(p + '/') for p in ESP32_PATHS)
        
        # Check if it's an admin path
        is_admin_path = any(path == p or path.startswith(p + '/') for p in ADMIN_PATHS)
        
        logger.debug("Path checks: public=%s, esp32=%s, admin=%s", is_public, is_esp32_endpoint, is_admin_path)
        
        # Handle ESP32 endpoints
        if is_esp32_endpoint:
            api_key = request.headers.get("X-API-Key")
            if api_key != settings.API_KEY:
                return Response(
                    content='{"detail":"Invalid or missing API Key"}',
                    status_code=401,
                    media_type="application/json"
                )
            return await call_next(request)
        
        # Handle authenticated endpoints
        if not is_public:
            # Get token from cookie or header
            token = request.cookies.get("access_token")
            
            if not token:
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
            
            if not token:
                logger.debug("No token found")
                if path.startswith("/api/"):
                    return Response(
                        content='{"detail":"Non authentifié"}',
                        status_code=401,
                        media_type="application/json"
                    )
                else:
                    return RedirectResponse(url="/login", status_code=302)
            
            # Verify token
            try:
                payload = PyJWT.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                logger.debug("Token decoded successfully: %s", payload)
                
                # Store user info in request state
                request.state.user = payload

                # Check admin access for admin paths
                if is_admin_path:
                    user_role = payload.get("role")
                    logger.debug("Admin path check - User role from token: %s", user_role)

                    # Role validation
                    if user_role != "admin":
                        logger.warning("Access denied - User role '%s' is not 'admin'", user_role)
                        if path.startswith("/api/"):
                            return Response(
                                content='{"detail":"Accès refusé. Cette section est réservée aux administrateurs."}',
                                status_code=403,
                                media_type="application/json"
                            )
                        else:
                            return RedirectResponse(url="/?error=access_denied", status_code=303)

                    logger.debug("Admin access granted for user with role: %s", user_role)
                
            except PyJWT.ExpiredSignatureError:
                logger.info("Token expired")
                if path.startswith("/api/"):
                    return Response(
                        content='{"detail":"Token expiré"}',
                        status_code=401,
                        media_type="application/json"
                    )
                else:
                    return RedirectResponse(url="/login?error=expired", status_code=302)
                    
            except PyJWT.PyJWTError as e:
                logger.info("Token validation error: %s", str(e))
                if path.startswith("/api/"):
                    return Response(
                        content='{"detail":"Token invalide"}',
                        status_code=401,
                        media_type="application/json"
                    )
                else:
                    return RedirectResponse(url="/login?error=invalid", status_code=302)
        
        return await call_next(request)


async def require_admin(request: Request, db: Session = Depends(get_db)):
    """
    Dependency for admin-only routes.
    Used as: @app.get("/admin/path", dependencies=[Depends(require_admin)])
    """
    user_data = getattr(request.state, "user", None)
    
    if not user_data:
        logger.debug("require_admin: No user data in request state")
        raise HTTPException(status_code=401, detail="Non authentifié")
    
    logger.debug("require_admin: Checking user %s with role %s", user_data.get('sub'), user_data.get('role'))
    
    user = db.query(models.User).filter(models.User.id == user_data["sub"]).first()
    
    if not user:
        logger.debug("require_admin: User %s not found in database", user_data['sub'])
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    
    if not user.is_active:
        logger.debug("require_admin: User %s account is disabled", user.username)
        raise HTTPException(status_code=401, detail="Compte désactivé")
    
    # **CRITICAL: Check role from BOTH token and database**
    token_role = user_data.get("role")
    db_role = user.role
    logger.debug("require_admin: Token role: %s, DB role: %s", token_role, db_role)
    
    if db_role != "admin":
        logger.warning("require_admin: Access denied - DB role is '%s', not 'admin'", db_role)
        raise HTTPException(
            status_code=403,
            detail="Accès refusé. Cette section est réservée aux administrateurs."
        )
    
    if token_role != "admin":
        logger.warning("require_admin: Token role '%s' doesn't match DB role '%s'", token_role, db_role)
        # Token mismatch - user should re-login
        raise HTTPException(
            status_code=401,
            detail="Session expirée. Veuillez vous reconnecter."
        )
    
    logger.debug("require_admin: Access granted for admin %s", user.username)
    return user