"""DocumentRecord and AuditLog ORM models."""
from __future__ import annotations

from typing import Optional
from sqlalchemy import String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.models.base import Base, TimestampMixin

class DocumentRecord(Base, TimestampMixin):
    """Tracks document ingestion status, namespaces, and chunking stats."""
    __tablename__ = "documents"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    knowledge_base_id: Mapped[Optional[str]] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    pinecone_namespace: Mapped[str] = mapped_column(String(100), default="default")
    chunks_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="indexed")

    user = relationship("User", back_populates="documents")
    knowledge_base = relationship("KnowledgeBase", back_populates="documents")



class AuditLog(Base, TimestampMixin):
    """Security and compliance audit trail."""
    __tablename__ = "audit_logs"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    details: Mapped[str] = mapped_column(Text, default="{}")
