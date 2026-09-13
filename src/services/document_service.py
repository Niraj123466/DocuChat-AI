"""Multi-tenant Document and Knowledge Base persistence service."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.models.document import DocumentRecord
from src.db.models.knowledge_base import KnowledgeBase
from src.core.logging import get_logger

logger = get_logger("document_service")

class DocumentService:
    """Manages multi-tenant document and knowledge base entities."""

    @staticmethod
    def get_user_storage_dir(user_id: str) -> Path:
        """Returns the isolated filesystem storage directory for a specific tenant."""
        base_dir = Path(settings.DOCUMENTS_DIR)
        user_dir = base_dir / f"user_{user_id}"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    @staticmethod
    async def get_or_create_default_kb(db: AsyncSession, user_id: str) -> KnowledgeBase:
        """Retrieves or provisions the default Knowledge Base for the tenant."""
        stmt = select(KnowledgeBase).where(KnowledgeBase.user_id == user_id).order_by(KnowledgeBase.created_at)
        res = await db.execute(stmt)
        kb = res.scalars().first()
        if not kb:
            kb = KnowledgeBase(
                user_id=user_id,
                name="Default Knowledge Base",
                description="Default isolated workspace knowledge base"
            )
            db.add(kb)
            await db.flush()
        return kb

    @staticmethod
    async def list_knowledge_bases(db: AsyncSession, user_id: str) -> List[KnowledgeBase]:
        """Lists knowledge bases owned by the authenticated tenant."""
        stmt = (
            select(KnowledgeBase)
            .where(KnowledgeBase.user_id == user_id)
            .options(selectinload(KnowledgeBase.documents))
            .order_by(desc(KnowledgeBase.created_at))
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def create_knowledge_base(
        db: AsyncSession,
        user_id: str,
        name: str,
        description: str = ""
    ) -> KnowledgeBase:
        """Creates a new knowledge base owned by the authenticated tenant."""
        kb = KnowledgeBase(
            user_id=user_id,
            name=name.strip() or "Untitled Knowledge Base",
            description=description.strip()
        )
        db.add(kb)
        await db.flush()
        logger.info(f"Created KnowledgeBase [{kb.id}] for user [{user_id}]")
        return kb

    @staticmethod
    async def get_knowledge_base(
        db: AsyncSession,
        kb_id: str,
        user_id: str
    ) -> Optional[KnowledgeBase]:
        """Fetches a specific knowledge base with strict tenant ownership verification."""
        stmt = (
            select(KnowledgeBase)
            .where(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user_id)
            .options(selectinload(KnowledgeBase.documents))
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def delete_knowledge_base(
        db: AsyncSession,
        kb_id: str,
        user_id: str
    ) -> bool:
        """Deletes a knowledge base if owned by user_id."""
        kb = await DocumentService.get_knowledge_base(db, kb_id, user_id)
        if not kb:
            return False
        await db.delete(kb)
        logger.info(f"Deleted KnowledgeBase [{kb_id}] for user [{user_id}]")
        return True

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        user_id: str,
        knowledge_base_id: Optional[str] = None
    ) -> List[DocumentRecord]:
        """Lists document records owned by the authenticated tenant."""
        stmt = select(DocumentRecord).where(DocumentRecord.user_id == user_id)
        if knowledge_base_id:
            stmt = stmt.where(DocumentRecord.knowledge_base_id == knowledge_base_id)
        stmt = stmt.order_by(desc(DocumentRecord.created_at))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_document(
        db: AsyncSession,
        document_id: str,
        user_id: str
    ) -> Optional[DocumentRecord]:
        """Fetches a single document record with tenant ownership verification."""
        stmt = select(DocumentRecord).where(DocumentRecord.id == document_id, DocumentRecord.user_id == user_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def record_document(
        db: AsyncSession,
        user_id: str,
        filename: str,
        file_size_bytes: int,
        chunks_count: int,
        knowledge_base_id: Optional[str] = None,
        pinecone_namespace: Optional[str] = None
    ) -> DocumentRecord:
        """Creates or updates a document catalog entry for the tenant."""
        stmt = select(DocumentRecord).where(
            DocumentRecord.user_id == user_id,
            DocumentRecord.filename == filename
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        namespace = pinecone_namespace or f"user_{user_id}"

        if existing:
            existing.file_size_bytes = file_size_bytes
            existing.chunks_count = chunks_count
            existing.pinecone_namespace = namespace
            existing.status = "indexed"
            if knowledge_base_id:
                existing.knowledge_base_id = knowledge_base_id
            await db.flush()
            return existing

        doc = DocumentRecord(
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            file_size_bytes=file_size_bytes,
            pinecone_namespace=namespace,
            chunks_count=chunks_count,
            status="indexed"
        )
        db.add(doc)
        await db.flush()
        logger.info(f"Recorded document [{doc.id}] '{filename}' for user [{user_id}]")
        return doc

    @staticmethod
    async def delete_document(
        db: AsyncSession,
        document_id: str,
        user_id: str
    ) -> bool:
        """Deletes a document record and local file if owned by user_id."""
        doc = await DocumentService.get_document(db, document_id, user_id)
        if not doc:
            return False

        # Remove local file
        user_dir = DocumentService.get_user_storage_dir(user_id)
        target_file = user_dir / doc.filename
        if target_file.exists():
            try:
                target_file.unlink()
            except Exception as e:
                logger.warning(f"Could not remove local file {target_file}: {e}")

        await db.delete(doc)
        logger.info(f"Deleted DocumentRecord [{document_id}] for user [{user_id}]")
        return True
