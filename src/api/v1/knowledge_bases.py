"""Knowledge Base management API endpoints with strict multi-tenant isolation."""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.services.document_service import DocumentService
from src.api.dependencies import get_current_user
from src.core.logging import get_logger

logger = get_logger("knowledge_bases_api")

router = APIRouter(prefix="/knowledge-bases", tags=["Knowledge Bases"])

class CreateKBRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Knowledge base name")
    description: Optional[str] = Field(default="", description="Knowledge base description")

class KBResponse(BaseModel):
    id: str
    name: str
    description: str
    documents_count: int
    created_at: str

@router.get("", response_model=List[KBResponse])
@router.get("/", response_model=List[KBResponse])
async def list_knowledge_bases(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Lists all knowledge bases owned by the authenticated tenant."""
    kbs = await DocumentService.list_knowledge_bases(db, user_id=current_user["id"])
    return [
        KBResponse(
            id=k.id,
            name=k.name,
            description=k.description,
            documents_count=len(k.documents),
            created_at=k.created_at.isoformat()
        )
        for k in kbs
    ]

@router.post("", response_model=KBResponse)
@router.post("/", response_model=KBResponse)
async def create_knowledge_base(
    request: CreateKBRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Creates a new knowledge base container owned by the authenticated tenant."""
    kb = await DocumentService.create_knowledge_base(
        db=db,
        user_id=current_user["id"],
        name=request.name,
        description=request.description or ""
    )
    return KBResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        documents_count=0,
        created_at=kb.created_at.isoformat()
    )

@router.get("/{kb_id}", response_model=KBResponse)
async def get_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves a specific knowledge base with strict tenant ownership validation."""
    kb = await DocumentService.get_knowledge_base(db, kb_id=kb_id, user_id=current_user["id"])
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found.")

    return KBResponse(
        id=kb.id,
        name=kb.name,
        description=kb.description,
        documents_count=len(kb.documents),
        created_at=kb.created_at.isoformat()
    )

@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Deletes a knowledge base with strict tenant ownership validation."""
    deleted = await DocumentService.delete_knowledge_base(db, kb_id=kb_id, user_id=current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found.")
    return {"status": "success", "message": "Knowledge base deleted."}
