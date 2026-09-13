"""Database engine configuration and async session management."""
from __future__ import annotations

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.core.config import settings
from src.core.logging import get_logger
from src.db.models import Base, User, Conversation, Message, DocumentRecord, AuditLog

logger = get_logger("db_session")

# Handle SQLite vs PostgreSQL async driver prefixes
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    db_url,
    echo=False,
    future=True,
    pool_pre_ping=True if not db_url.startswith("sqlite") else False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def init_db() -> None:
    """Creates database tables on application initialization."""
    try:
        logger.info(f"Initializing database schema using URL: {db_url}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failure: {e}", exc_info=True)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency providing async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session rolled back due to error: {e}")
            raise
        finally:
            await session.close()
