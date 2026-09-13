"""Unified v1 API router for DocuChat-AI."""
from __future__ import annotations

from fastapi import APIRouter
from src.api.v1.health import router as health_router
from src.api.v1.auth import router as auth_router
from src.api.v1.chat import router as chat_router
from src.api.v1.conversations import router as conversations_router
from src.api.v1.documents import router as documents_router
from src.api.v1.knowledge_bases import router as knowledge_bases_router
from src.api.v1.whatsapp import router as whatsapp_router
from src.api.v1.eval import router as eval_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(knowledge_bases_router)
api_v1_router.include_router(whatsapp_router)
api_v1_router.include_router(eval_router)


__all__ = ["api_v1_router"]
