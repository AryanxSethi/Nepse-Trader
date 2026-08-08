"""Async SQLAlchemy engine, session factory, and base model.

Uses ``aiosqlite`` for async SQLite access.
"""

import os

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import DB_PATH, DATA_DIR

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite+aiosqlite:///{DB_PATH.as_posix()}",
)

DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"timeout": 15},
    pool_pre_ping=True,
)


@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Enable WAL journaling and a busy timeout to avoid locked-database errors."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=10000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


async def init_db():
    """Create all tables defined in :mod:`models` if they do not exist."""
    async with engine.begin() as conn:
        from app.db.models import Security, DailyPrice, Signal, PortfolioHolding
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    """Yield an async database session (for FastAPI dependency injection)."""
    async with async_session() as session:
        yield session
