"""Legacy Web Chatbot API entrypoint.

Delegates directly to the centralized application in src.api.app
while preserving legacy imports and endpoint contracts.
"""
from __future__ import annotations

import uvicorn
from src.api.app import app
from src.api.v1.chat import ChatRequest, ChatResponse

__all__ = ["app", "ChatRequest", "ChatResponse"]

if __name__ == "__main__":
    uvicorn.run("src.main.chatbotapi:app", host="0.0.0.0", port=8000, reload=True)