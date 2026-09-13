"""Health check and diagnostic endpoints."""
from __future__ import annotations

from typing import Dict, Any
from fastapi import APIRouter
from src.core.config import settings

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

@router.get("", response_model=Dict[str, Any])
@router.get("/", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """System health check and dependency connectivity status."""
    keys = settings.validate_keys()
    
    # Check documents folder
    docs_exist = settings.DOCUMENTS_DIR.exists()
    doc_count = len(list(settings.DOCUMENTS_DIR.glob("*.*"))) if docs_exist else 0

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {
            "google_gemini_configured": keys["google_api_key"],
            "pinecone_configured": keys["pinecone_api_key"],
            "whatsapp_configured": keys["whatsapp_token"],
        },
        "storage": {
            "documents_dir": str(settings.DOCUMENTS_DIR),
            "documents_count": doc_count,
        }
    }
