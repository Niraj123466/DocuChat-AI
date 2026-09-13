"""User ORM model for persistent authentication and RBAC."""
from __future__ import annotations

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.models.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    """Stores user accounts, credentials, and access roles."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("DocumentRecord", back_populates="user", cascade="all, delete-orphan")
    knowledge_bases = relationship("KnowledgeBase", back_populates="user", cascade="all, delete-orphan")

