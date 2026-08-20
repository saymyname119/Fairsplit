"""
shared/db/session.py
─────────────────────
Database engine and session factory.

FastAPI + SQLAlchemy 2.0 async pattern:
  - AsyncEngine   → one per process, created once at startup
  - async_sessionmaker → factory; each request gets a fresh AsyncSession
  - get_db()      → FastAPI dependency that yields a session and handles
                    commit/rollback automatically

Why async?
  FastAPI is async-first. Using SQLAlchemy's async extension means DB queries
  don't block the event loop, letting the app handle many concurrent requests
  with a small thread pool. In practice this matters most for balance reads
  under load (Prompt 3).
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Engine ────────────────────────────────────────────────────────────────────
# pool_pre_ping=True: test connections before using them from the pool.
# This prevents "connection reset by peer" errors after Postgres restarts.
# echo=True in development prints all SQL to the console — turn off in prod.
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=(settings.environment == "development"),
    # pool_size and max_overflow tune connection pool size.
    # Default (5 / 10) is fine for a monolith; tune per-service when splitting.
    pool_size=5,
    max_overflow=10,
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    # expire_on_commit=False: after a commit, ORM objects remain accessible
    # without triggering a fresh DB query. Important for async code where
    # implicit lazy-loads would error outside a session context.
)


async def get_db() -> AsyncSession:  # type: ignore[return]
    """
    FastAPI dependency: yields an AsyncSession for one request.

    Usage in a route:
        @router.post("/")
        async def create(db: AsyncSession = Depends(get_db)):
            ...

    The session is committed on success and rolled back on exception.
    The finally block ensures the session is always closed.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Health check: verifies the DB is reachable. Used by GET /healthz."""
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False
