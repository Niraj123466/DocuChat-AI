"""Structured logging system for DocuChat-AI.

Provides unified JSON or formatted console logging across all modules,
replacing unformatted print() statements with context-aware loggers.
"""
from __future__ import annotations

import logging
import sys
from typing import Any, Dict
from src.core.config import settings

class StructuredFormatter(logging.Formatter):
    """Formats log records as structured text or key-value entries."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        log_entry: Dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "props") and isinstance(record.props, dict):
            log_entry.update(record.props)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Colorized/readable console format for development
        if settings.ENVIRONMENT == "development":
            color = "\033[36m" if record.levelname == "INFO" else "\033[33m" if record.levelname == "WARNING" else "\033[31m" if record.levelname in ("ERROR", "CRITICAL") else "\033[37m"
            reset = "\033[0m"
            extra = f" | {record.props}" if hasattr(record, "props") else ""
            return f"{color}[{timestamp}] [{record.levelname:<7}] [{record.name}]:{reset} {record.getMessage()}{extra}"
        
        import json
        return json.dumps(log_entry)


def get_logger(name: str) -> logging.Logger:
    """Obtain a configured structured logger instance."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
        logger.setLevel(log_level)
        logger.propagate = False
    return logger

# Global default logger
logger = get_logger("docuchat")
