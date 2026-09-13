"""Message ORM model storing turns, citations, and latency metrics."""
from __future__ import annotations

import json
from typing import Optional, Any, List, Dict
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.models.base import Base, TimestampMixin

class Message(Base, TimestampMixin):
    """Stores individual conversational turns with citations and metadata."""
    __tablename__ = "messages"

    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(50), nullable=False)  # "user", "assistant", "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="[]")
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="{}")

    conversation = relationship("Conversation", back_populates="messages")

    @property
    def citations(self) -> List[Dict[str, Any]]:
        if not self.citations_json:
            return []
        try:
            return json.loads(self.citations_json)
        except Exception:
            return []

    @citations.setter
    def citations(self, value: List[Dict[str, Any]]):
        self.citations_json = json.dumps(value) if value else "[]"

    @property
    def meta(self) -> Dict[str, Any]:
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {}

    @meta.setter
    def meta(self, value: Dict[str, Any]):
        self.metadata_json = json.dumps(value) if value else "{}"
