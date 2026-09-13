"""Document ingestion API endpoint."""
from __future__ import annotations

from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
import shutil

from src.Uploader.uploader_pinecone import DocumentUploader
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("upload_api")

app = FastAPI(title="DocuChat Document Ingestion API")

class UploadResponse(BaseModel):
    status: str
    message: str
    document: Optional[str] = None
    chunks_uploaded: Optional[int] = None

@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: Optional[UploadFile] = File(None)):
    """Upload and ingest a document into the Pinecone vector index."""
    try:
        uploader = DocumentUploader()
        target_path = None

        if file:
            # Save uploaded file to documents directory
            save_dir = settings.DOCUMENTS_DIR
            save_dir.mkdir(parents=True, exist_ok=True)
            target_path = save_dir / file.filename
            with open(target_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            logger.info(f"Received file upload saved to {target_path}")

        result = uploader.upload_documents(file_path=target_path)
        return UploadResponse(
            status="success",
            message="Document successfully processed and indexed.",
            document=result.get("document"),
            chunks_uploaded=result.get("chunks_uploaded")
        )
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)