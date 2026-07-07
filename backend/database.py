"""Async SQLAlchemy engine, session factory, and base model.

Uses ``aiosqlite`` for async SQLite access.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import DB_PATH

DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


async def init_db():
    """Create all tables defined in :mod:`models` if they do not exist."""
    async with engine.begin() as conn:
        from models import Security, DailyPrice, Signal, PortfolioHolding
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    """Yield an async database session (for FastAPI dependency injection)."""
    async with async_session() as session:
        yield session
