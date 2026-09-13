"""Local document loader strategy using Docling."""
from __future__ import annotations

from pathlib import Path
from src.utils.vector_db.loader_strategies.base import DocumentLoaderStrategy
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("local_loader")

class LocalLoader(DocumentLoaderStrategy):
    def load_documents(self, path: str | Path) -> str:
        target_path = Path(path)
        if not target_path.exists():
            raise FileNotFoundError(f"Document not found at: {target_path}")

        logger.info(f"Converting document: {target_path}")
        # Directly read text and markdown files
        if target_path.suffix.lower() in (".txt", ".md", ".json", ".csv", ".log"):
            logger.info(f"Direct text read for {target_path}")
            return target_path.read_text(encoding="utf-8", errors="ignore")

        try:
            from docling.document_converter import DocumentConverter
            result = DocumentConverter().convert(str(target_path))
            document = result.document
            markdown_output = document.export_to_markdown()
            logger.info(f"Document converted via Docling ({len(markdown_output)} characters)")
            return markdown_output
        except (ImportError, Exception) as docling_err:
            logger.warning(f"Docling conversion unavailable ({docling_err}). Falling back to pypdf.")
            from pypdf import PdfReader
            reader = PdfReader(str(target_path))
            text_parts = []
            for i, page in enumerate(reader.pages):
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(f"--- Page {i+1} ---\n" + extracted)
            output = "\n\n".join(text_parts)
            logger.info(f"Document converted via pypdf fallback ({len(output)} characters)")
            return output

if __name__ == "__main__":
    sample_doc = settings.DOCUMENTS_DIR / "MIREMS.pdf"
    if sample_doc.exists():
        loader = LocalLoader()
        out = loader.load_documents(path=sample_doc)
        print(f"Loaded {len(out)} chars from {sample_doc}")
    else:
        print(f"Sample document not found at {sample_doc}")
