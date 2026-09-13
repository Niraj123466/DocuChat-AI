"""KnowledgeBase ORM model for multi-tenant document collections."""
from __future__ import annotations

from typing import List
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.models.base import Base, TimestampMixin

class KnowledgeBase(Base, TimestampMixin):
    """Represents an isolated knowledge base container owned by a user."""
    __tablename__ = "knowledge_bases"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    user = relationship("User", back_populates="knowledge_bases")
    documents: Mapped[List["DocumentRecord"]] = relationship(
        "DocumentRecord",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        order_by="DocumentRecord.created_at"
    )
