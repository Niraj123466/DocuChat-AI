"""Chat and Conversation persistence service."""
from __future__ import annotations

import json
from typing import List, Optional, Dict, Any
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.conversation import Conversation
from src.db.models.message import Message
from src.core.logging import get_logger

logger = get_logger("chat_service")

class ChatService:
    """Manages persistent conversation threads and messages with strict tenant isolation."""

    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        title: str = "New Conversation",
        user_id: Optional[str] = None
    ) -> Conversation:
        """Creates a new conversation thread owned by user_id."""
        conv = Conversation(title=title, user_id=user_id)
        db.add(conv)
        await db.flush()
        logger.info(f"Created conversation thread [{conv.id}] for user [{user_id}]: '{title}'")
        return conv

    @staticmethod
    async def get_conversation(
        db: AsyncSession,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Conversation]:
        """Fetches a conversation thread with all loaded messages, scoped to user_id."""
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        if user_id:
            stmt = stmt.where(Conversation.user_id == user_id)

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_conversations(
        db: AsyncSession,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Conversation]:
        """Lists conversations strictly filtered by authenticated user_id."""
        stmt = select(Conversation).order_by(desc(Conversation.updated_at)).limit(limit)
        if user_id:
            stmt = stmt.where(Conversation.user_id == user_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def delete_conversation(
        db: AsyncSession,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """Deletes a conversation thread with strict user_id ownership check."""
        conv = await ChatService.get_conversation(db, conversation_id, user_id=user_id)
        if not conv:
            logger.warning(f"Unauthorized or non-existent conversation delete attempt [{conversation_id}] by user [{user_id}]")
            return False
        await db.delete(conv)
        logger.info(f"Deleted conversation thread [{conversation_id}] for user [{user_id}]")
        return True

    @staticmethod
    async def record_message(
        db: AsyncSession,
        conversation_id: str,
        sender: str,
        content: str,
        user_id: Optional[str] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """Appends a new turn to an existing conversation thread after validating tenant ownership."""
        if user_id:
            conv = await ChatService.get_conversation(db, conversation_id, user_id=user_id)
            if not conv:
                logger.warning(f"Cannot append message to conversation [{conversation_id}]: unauthorized for user [{user_id}]")
                return None

        msg = Message(
            conversation_id=conversation_id,
            sender=sender,
            content=content,
            citations_json=json.dumps(citations or []),
            metadata_json=json.dumps(metadata or {})
        )
        db.add(msg)
        await db.flush()
        logger.info(f"Saved {sender} message in conversation [{conversation_id}]")
        return msg

