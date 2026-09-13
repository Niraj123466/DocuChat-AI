"""DocuChat-AI Legacy settings adapter.

This file delegates directly to src.core.config.settings to ensure backwards
compatibility while consolidating all configuration in one place.
"""
from src.core.config import settings, BASE_DIR

GOOGLE_API_KEY = settings.GOOGLE_API_KEY
PINECONE_API_KEY = settings.PINECONE_API_KEY
PINECONE_INDEX_NAME = settings.PINECONE_INDEX_NAME
PINECONE_REGION = settings.PINECONE_REGION
PINECONE_HOST = settings.PINECONE_HOST
WHATSAPP_TOKEN = settings.WHATSAPP_TOKEN
PHONE_NUMBER_ID = settings.PHONE_NUMBER_ID
WHATSAPP_VERIFY_TOKEN = settings.WHATSAPP_VERIFY_TOKEN
WHATSAPP_APP_SECRET = settings.WHATSAPP_APP_SECRET
GUARDRAILS_API_KEY = settings.GUARDRAILS_API_KEY
ORGANIZATION_NAME = settings.ORGANIZATION_NAME
DOCUMENTS_DIR = settings.DOCUMENTS_DIR

__all__ = [
    "BASE_DIR",
    "GOOGLE_API_KEY",
    "PINECONE_API_KEY",
    "PINECONE_INDEX_NAME",
    "PINECONE_REGION",
    "PINECONE_HOST",
    "WHATSAPP_TOKEN",
    "PHONE_NUMBER_ID",
    "WHATSAPP_VERIFY_TOKEN",
    "WHATSAPP_APP_SECRET",
    "GUARDRAILS_API_KEY",
    "ORGANIZATION_NAME",
    "DOCUMENTS_DIR",
    "settings",
]