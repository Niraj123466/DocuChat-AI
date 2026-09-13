"""FastAPI dependencies for authentication, role verification, and rate limiting."""
from __future__ import annotations

from typing import Optional, Dict, Any
from fastapi import Request, Response, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.security import JWTHandler, UserStore
from src.core.rate_limiter import rate_limiter
from src.core.logging import get_logger
from src.db.session import get_db

logger = get_logger("api_dependencies")

security_bearer = HTTPBearer(auto_error=False)

def get_client_ip(request: Request) -> str:
    """Extracts client IP considering proxy forwarding headers."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


async def check_rate_limit(request: Request, response: Response):
    """Enforces per-client rate limiting and injects rate limit telemetry headers."""
    client_id = get_client_ip(request)
    allowed, remaining, retry_after = rate_limiter.check_rate_limit(client_id, limit=30)

    response.headers["X-RateLimit-Limit"] = "30"
    response.headers["X-RateLimit-Remaining"] = str(remaining)

    if not allowed:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds."
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> Optional[Dict[str, Any]]:
    """Extracts user from Bearer JWT token if supplied, returning None if unauthenticated."""
    if not credentials or not credentials.credentials:
        return None

    try:
        payload = JWTHandler.decode_access_token(credentials.credentials)
        sub = payload.get("sub")
        if not sub:
            return None
        from src.services.user_service import UserService
        user = await UserService.get_by_id(db, sub)
        if not user:
            user = await UserService.get_by_email(db, sub)
        if user:
            return {
                "id": user.id,
                "email": user.email,
                "name": getattr(user, "name", "") or user.email.split("@")[0],
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at)
            }
        mem_user = UserStore.get_by_email(payload.get("email") or sub)
        return mem_user
    except Exception as e:
        logger.warning(f"Optional auth token invalid: {e}")
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Requires a valid Bearer JWT token, throwing 401 Unauthorized if missing, expired, or invalid."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = JWTHandler.decode_access_token(credentials.credentials)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Token missing subject claim.", headers={"WWW-Authenticate": "Bearer"})

        from src.services.user_service import UserService
        user = await UserService.get_by_id(db, sub)
        if not user:
            user = await UserService.get_by_email(db, sub)

        if user:
            return {
                "id": user.id,
                "email": user.email,
                "name": getattr(user, "name", "") or user.email.split("@")[0],
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at)
            }

        mem_user = UserStore.get_by_email(payload.get("email") or sub)
        if mem_user:
            return mem_user

        raise HTTPException(status_code=401, detail="User account not found.", headers={"WWW-Authenticate": "Bearer"})
    except ValueError as ve:
        raise HTTPException(status_code=401, detail=str(ve), headers={"WWW-Authenticate": "Bearer"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failure: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication credentials.", headers={"WWW-Authenticate": "Bearer"})



def require_role(required_role: str):
    """Factory creating dependency to enforce Role-Based Access Control (RBAC)."""
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "user")
        if user_role != required_role and user_role != "admin":
            logger.warning(f"Forbidden access: User '{current_user.get('email')}' with role '{user_role}' requires '{required_role}'")
            raise HTTPException(
                status_code=403,
                detail=f"Access forbidden: requires '{required_role}' privilege."
            )
        return current_user
    return role_checker
