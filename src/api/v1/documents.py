"""Document management and ingestion API endpoints with background task support."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Query, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import get_logger
from src.Uploader.uploader_pinecone import DocumentUploader

from src.db.session import get_db
from src.services.document_service import DocumentService
from src.api.dependencies import get_current_user

logger = get_logger("documents_api")

router = APIRouter(prefix="/documents", tags=["Documents & Ingestion"])

class DocumentItem(BaseModel):
    id: Optional[str] = None
    name: str
    size_bytes: int
    modified_at: str

class DocumentListResponse(BaseModel):
    documents_dir: str
    total_files: int
    files: List[DocumentItem]

class IngestResponse(BaseModel):
    status: str
    message: str
    document: Optional[str] = None
    chunks_uploaded: Optional[int] = None
    document_id: Optional[str] = None

def _run_background_ingestion(file_path: Optional[Path], user_id: Optional[str]) -> None:
    """Worker function executed asynchronously in background with tenant context."""
    try:
        logger.info(f"Background ingestion worker started for: {file_path} (User: {user_id})")
        uploader = DocumentUploader()
        result = uploader.upload_documents(file_path=file_path, user_id=user_id)
        logger.info(f"Background ingestion complete: {result}")
    except Exception as e:
        logger.error(f"Background ingestion error: {e}", exc_info=True)

@router.get("", response_model=DocumentListResponse)
@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Lists only documents owned by the authenticated tenant."""
    user_id = current_user["id"]
    user_dir = DocumentService.get_user_storage_dir(user_id)
    doc_records = await DocumentService.list_documents(db, user_id=user_id)

    items: List[DocumentItem] = []
    seen_files = set()

    for r in doc_records:
        seen_files.add(r.filename)
        mod_time = r.updated_at.isoformat() if hasattr(r.updated_at, "isoformat") else str(r.updated_at)
        items.append(DocumentItem(id=r.id, name=r.filename, size_bytes=r.file_size_bytes, modified_at=mod_time))

    # Also list any local files in the tenant directory not yet in DB
    if user_dir.exists():
        for f in user_dir.glob("*.*"):
            if f.is_file() and not f.name.startswith(".") and f.name not in seen_files:
                stat = f.stat()
                from datetime import datetime, timezone
                mod_time = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                items.append(DocumentItem(id=None, name=f.name, size_bytes=stat.st_size, modified_at=mod_time))

    return DocumentListResponse(
        documents_dir=str(user_dir),
        total_files=len(items),
        files=items
    )

@router.post("/upload", response_model=IngestResponse)
async def upload_and_ingest(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    async_mode: bool = Query(False, description="Process document ingestion asynchronously in background"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Uploads and indexes a document strictly scoped to the authenticated tenant."""
    try:
        user_id = current_user["id"]
        user_dir = DocumentService.get_user_storage_dir(user_id)

        target_file_path = None
        doc_name = "default"
        file_size = 0

        if file and file.filename:
            doc_name = Path(file.filename).name  # sanitize filename
            target_file_path = user_dir / doc_name
            with open(target_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            file_size = target_file_path.stat().st_size
            logger.info(f"Saved uploaded document for tenant [{user_id}]: {target_file_path}")
        else:
            # Fallback to sample document in default docs
            default_path = settings.DOCUMENTS_DIR / "MIREMS.pdf"
            if default_path.exists():
                doc_name = "MIREMS.pdf"
                target_file_path = user_dir / doc_name
                shutil.copy(default_path, target_file_path)
                file_size = target_file_path.stat().st_size

        if async_mode:
            background_tasks.add_task(_run_background_ingestion, target_file_path, user_id)
            return IngestResponse(
                status="processing",
                message="Document upload received. Ingestion task is executing in the background.",
                document=doc_name,
                chunks_uploaded=None
            )

        # Synchronous execution with tenant isolation
        uploader = DocumentUploader()
        result = uploader.upload_documents(file_path=target_file_path, user_id=user_id)
        chunks = result.get("chunks_uploaded", 0)

        # Persist DocumentRecord in DB
        default_kb = await DocumentService.get_or_create_default_kb(db, user_id=user_id)
        doc_record = await DocumentService.record_document(
            db=db,
            user_id=user_id,
            filename=doc_name,
            file_size_bytes=file_size,
            chunks_count=chunks,
            knowledge_base_id=default_kb.id,
            pinecone_namespace=f"user_{user_id}"
        )

        return IngestResponse(
            status="success",
            message="Document uploaded and indexed successfully with tenant isolation.",
            document=result.get("document"),
            chunks_uploaded=chunks,
            document_id=doc_record.id
        )
    except Exception as e:
        logger.error(f"Upload and indexing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Deletes a document with strict tenant ownership validation."""
    deleted = await DocumentService.delete_document(db, document_id=document_id, user_id=current_user["id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"status": "success", "message": "Document deleted successfully."}

