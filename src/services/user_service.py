"""Database-backed User management and authentication service."""
from __future__ import annotations

from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.user import User
from src.db.models.knowledge_base import KnowledgeBase
from src.core.security import PasswordHasher
from src.core.logging import get_logger

logger = get_logger("user_service")

class UserService:
    """Manages user persistence, credentials, and tenant default provisioning."""

    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str,
        password: str,
        name: str = "",
        role: str = "user"
    ) -> User:
        """Registers a new user in the database with bcrypt password hashing and default KB."""
        normalized_email = email.lower().strip()
        stmt = select(User).where(User.email == normalized_email)
        existing = await db.execute(stmt)
        if existing.scalar_one_or_none():
            raise ValueError(f"User with email '{normalized_email}' already exists.")

        hashed_pw = PasswordHasher.hash_password(password)
        user = User(
            email=normalized_email,
            hashed_password=hashed_pw,
            name=name.strip() or normalized_email.split("@")[0],
            role=role if role in ("user", "admin") else "user",
            is_active=True
        )
        db.add(user)
        await db.flush()

        # Provision a default isolated Knowledge Base for the new tenant
        default_kb = KnowledgeBase(
            user_id=user.id,
            name="Default Knowledge Base",
            description="Default isolated workspace knowledge base"
        )
        db.add(default_kb)
        await db.flush()

        logger.info(f"Created user [{user.id}]: {user.email} (Role: {user.role})")
        return user

    @staticmethod
    async def authenticate(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """Authenticates user credentials against the persistent database."""
        normalized_email = email.lower().strip()
        stmt = select(User).where(User.email == normalized_email, User.is_active == True)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            return None
        if not PasswordHasher.verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        """Fetches user account by unique user ID."""
        stmt = select(User).where(User.id == user_id, User.is_active == True)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Fetches user account by email address."""
        stmt = select(User).where(User.email == email.lower().strip(), User.is_active == True)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
