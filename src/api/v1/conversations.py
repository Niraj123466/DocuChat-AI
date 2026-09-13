"""Conversations and Chat History management endpoints."""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.services.chat_service import ChatService
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/conversations", tags=["Conversations & History"])

class CreateConversationRequest(BaseModel):
    title: str = Field(default="New Conversation", description="Thread title")

class MessageItemResponse(BaseModel):
    id: str
    sender: str
    content: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str

class ConversationSummaryResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str

class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[MessageItemResponse]

@router.get("", response_model=List[ConversationSummaryResponse])
@router.get("/", response_model=List[ConversationSummaryResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Lists conversation threads owned by the authenticated tenant."""
    threads = await ChatService.list_conversations(db, user_id=current_user["id"])
    return [
        ConversationSummaryResponse(
            id=t.id,
            title=t.title,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat()
        )
        for t in threads
    ]

@router.post("", response_model=ConversationSummaryResponse)
@router.post("/", response_model=ConversationSummaryResponse)
async def create_conversation(
    request: CreateConversationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Initializes a new threaded conversation owned by the authenticated tenant."""
    conv = await ChatService.create_conversation(db, title=request.title, user_id=current_user["id"])
    return ConversationSummaryResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat()
    )

@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves full conversation turn history with strict tenant ownership validation."""
    conv = await ChatService.get_conversation(db, conversation_id, user_id=current_user["id"])
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    messages_out = [
        MessageItemResponse(
            id=m.id,
            sender=m.sender,
            content=m.content,
            citations=m.citations,
            created_at=m.created_at.isoformat()
        )
        for m in conv.messages
    ]

    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        messages=messages_out
    )

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Deletes a conversation thread with strict tenant ownership validation."""
    deleted = await ChatService.delete_conversation(db, conversation_id, user_id=current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"status": "success", "message": "Conversation deleted."}

