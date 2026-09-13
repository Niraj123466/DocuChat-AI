"""Authentication and User Profile endpoints."""
from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import UserStore, JWTHandler
from src.services.user_service import UserService
from src.db.session import get_db
from src.api.dependencies import get_current_user
from src.core.logging import get_logger

logger = get_logger("auth_api")

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])

class RegisterRequest(BaseModel):
    name: Optional[str] = Field(default="", description="User display name")
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    role: str = Field(default="user", description="Requested role: user or admin")

class LoginRequest(BaseModel):
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", description="User email address")
    password: str = Field(..., description="User password")

class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: str = ""
    role: str
    is_active: bool
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserProfileResponse

@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Registers a new user account with bcrypt password hashing, default KB, and issues signed JWT."""
    try:
        user = await UserService.create_user(
            db=db,
            email=request.email,
            password=request.password,
            name=request.name or "",
            role=request.role if request.role in ("user", "admin") else "user"
        )
        # Mirror in UserStore for in-memory fallback compatibility
        try:
            UserStore.register_user(request.email, request.password, role=user.role)
        except Exception:
            pass

        token = JWTHandler.create_access_token(
            subject=user.id,
            role=user.role,
            extra_claims={"email": user.email, "name": user.name or "", "user_id": user.id}
        )

        user_profile = UserProfileResponse(
            id=user.id,
            email=user.email,
            name=user.name or "",
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at),
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_profile
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Registration failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal registration failure.")

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticates credentials using bcrypt and issues signed JWT access token."""
    user = await UserService.authenticate(db=db, email=request.email, password=request.password)
    user_id = None
    user_email = None
    user_name = ""
    user_role = "user"
    user_active = True
    user_created_at = ""

    if user:
        user_id = user.id
        user_email = user.email
        user_name = user.name or ""
        user_role = user.role
        user_active = user.is_active
        user_created_at = user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at)
    else:
        # Fallback to UserStore (in-memory fixtures)
        mem_user = UserStore.authenticate(email=request.email, password=request.password)
        if mem_user:
            user_id = mem_user["id"]
            user_email = mem_user["email"]
            user_name = mem_user.get("name", "")
            user_role = mem_user["role"]
            user_active = mem_user["is_active"]
            user_created_at = str(mem_user["created_at"])
        else:
            logger.warning(f"Failed login attempt for email: {request.email}")
            raise HTTPException(
                status_code=401,
                detail="Invalid email address or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    token = JWTHandler.create_access_token(
        subject=user_id,
        role=user_role,
        extra_claims={"email": user_email, "name": user_name, "user_id": user_id}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=24 * 3600,
        user=UserProfileResponse(
            id=user_id,
            email=user_email,
            name=user_name,
            role=user_role,
            is_active=user_active,
            created_at=user_created_at,
        )
    )

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns profile information for the authenticated user session."""
    return UserProfileResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user.get("name", ""),
        role=current_user["role"],
        is_active=current_user["is_active"],
        created_at=str(current_user["created_at"]),
    )

