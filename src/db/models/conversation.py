"""Conversation thread ORM model."""
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.models.base import Base, TimestampMixin

class Conversation(Base, TimestampMixin):
    """Represents a threaded chat session."""
    __tablename__ = "conversations"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="New Conversation", nullable=False)

    user = relationship("User", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
