"""Type-safe application configuration for DocuChat-AI.

Supports loading from environment variables, .env files, and provides
sensible production defaults without any hardcoded filesystem paths.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

# Base directory is the project root (DocuChat-AI)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Attempt to load .env file if dotenv is present
try:
    from dotenv import load_dotenv
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass

class Settings:
    """Production settings container with environment variable resolution."""

    def __init__(self) -> None:
        # General Application
        self.APP_NAME: str = os.getenv("APP_NAME", "DocuChat-AI")
        self.APP_VERSION: str = os.getenv("APP_VERSION", "2.0.0")
        self.ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
        self.DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

        # Paths
        self.BASE_DIR: Path = BASE_DIR
        doc_dir = os.getenv("DOCUMENTS_DIR")
        self.DOCUMENTS_DIR: Path = Path(doc_dir) if doc_dir else (BASE_DIR / "documents")

        # LLM & AI Services
        self.GOOGLE_API_KEY: str = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        )
        self.GUARDRAILS_API_KEY: Optional[str] = os.getenv("GUARDRAILS_API_KEY")
        self.ORGANIZATION_NAME: Optional[str] = os.getenv("ORGANIZATION_NAME", "DocuChat")

        # Vector Database (Pinecone)
        self.PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
        self.PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "query-agent-index")
        self.PINECONE_REGION: Optional[str] = os.getenv("PINECONE_REGION")
        self.PINECONE_HOST: Optional[str] = os.getenv("PINECONE_HOST")
        self.TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
        self.SCORE_THRESHOLD: float = float(os.getenv("RAG_SCORE_THRESHOLD", "0.10"))

        # WhatsApp Integration
        self.WHATSAPP_TOKEN: Optional[str] = os.getenv("WA_ACCESS_TOKEN") or os.getenv("WHATSAPP_TOKEN")
        self.PHONE_NUMBER_ID: Optional[str] = os.getenv("WA_PHONE_NUMBER_ID") or os.getenv("PHONE_NUMBER_ID")
        self.WHATSAPP_VERIFY_TOKEN: str = (
            os.getenv("WHATSAPP_VERIFY_TOKEN")
            or os.getenv("WA_VERIFY_TOKEN")
            or "docuchat_verify_token_prod"
        )
        self.WHATSAPP_APP_SECRET: Optional[str] = os.getenv("WHATSAPP_APP_SECRET")

        # Security & Auth
        self.JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "docuchat-enterprise-insecure-secret-key-32chars")
        self.JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))

        # Networking & CORS
        cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
        if cors_raw.startswith("[") and cors_raw.endswith("]"):
            try:
                import json
                parsed = json.loads(cors_raw)
                self.CORS_ORIGINS: List[str] = [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                self.CORS_ORIGINS: List[str] = [origin.strip().strip("'\"") for origin in cors_raw.strip("[]").split(",") if origin.strip()]
        else:
            self.CORS_ORIGINS: List[str] = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]

        # Storage & Persistence
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR}/docuchat.db")
        self.REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Workflow Tuning
        self.MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    def validate_keys(self) -> dict[str, bool]:
        """Verify presence of required service API keys."""
        return {
            "google_api_key": bool(self.GOOGLE_API_KEY),
            "pinecone_api_key": bool(self.PINECONE_API_KEY),
            "whatsapp_token": bool(self.WHATSAPP_TOKEN),
        }

settings = Settings()
