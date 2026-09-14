"""
api/app.py
───────────
FastAPI application factory and startup/shutdown lifecycle.

This file is the composition root — the only place where:
  1. Concrete service implementations are instantiated
  2. Dependencies are wired together
  3. Event bus handlers are registered
  4. Routers are mounted

Why composition root?
  Every other file depends on interfaces (IUserService, ILedgerService, etc.).
  Concrete classes are only named here. To swap UserService for a mock in tests,
  we override the FastAPI dependency — no other file needs to change.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import ai, auth, expenses, groups, health, invitations, ledger, users
from modules.notification import register_notification_handlers
from shared.cache import balance_cache_key, close_redis, invalidate
from shared.config import get_settings
from shared.db.session import check_db_connection
from shared.errors import AppError
from shared.events import DomainEvent, get_event_bus
from shared.middleware.error_handler import app_error_handler, unhandled_exception_handler

logger = logging.getLogger(__name__)
settings = get_settings()


def _handle_cache_invalidation(event: DomainEvent) -> None:
    """
    Event handler: invalidate the group balance cache when balances change.
    Subscribed to ExpenseCreated and SettlementRecorded events.

    Why synchronous wrapper around async invalidate()?
      The InProcessEventBus fires handlers synchronously (by design — see
      shared/events/event_bus.py). Cache invalidation is a DEL command that
      takes < 1ms, so the impact on response time is negligible. When we move
      to Kafka, this handler becomes a consumer that can run async natively.
    """
    import asyncio

    group_id = getattr(event, "group_id", None)
    if group_id:
        key = balance_cache_key(group_id)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(invalidate(key))
        except RuntimeError:
            # No running event loop (e.g., in tests) — skip cache invalidation
            logger.debug("No event loop for cache invalidation — skipping")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler (replaces deprecated on_event).
    Code before `yield` runs at startup; code after runs at shutdown.
    """
    # ── Startup ───────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.DEBUG if not settings.is_production else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger.info("Starting Splitwise Clone [%s]", settings.environment)

    # Wire notification observers to the event bus
    bus = get_event_bus()
    register_notification_handlers(bus)

    # Wire cache invalidation to the event bus
    bus.subscribe("expense.ExpenseCreated", _handle_cache_invalidation)
    bus.subscribe("ledger.SettlementRecorded", _handle_cache_invalidation)
    logger.info("Cache invalidation handlers registered for balance cache")

    # Verify infrastructure connectivity
    db_ok = await check_db_connection()
    if not db_ok:
        logger.error("Database connection failed at startup")
    else:
        logger.info("Database connection OK")

    logger.info("Application startup complete")

    yield  # ← app runs here

    # ── Shutdown ──────────────────────────────────────────────────────────
    logger.info("Application shutting down")
    await close_redis()
    logger.info("Redis connection closed")


def create_app() -> FastAPI:
    """
    Application factory.
    Returns a configured FastAPI app instance.
    Using a factory function (not module-level) makes it easy to create
    isolated app instances for testing.
    """
    app = FastAPI(
        title="Splitwise Clone",
        description=(
            "A Splitwise-style expense splitting app. "
            "Modular monolith, microservice-ready. Built as a portfolio project."
        ),
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    if settings.is_production:
        cors_allowed: set[str] = set()
        if settings.app_base_url:
            cors_allowed.add(settings.app_base_url.rstrip("/"))
        if settings.cors_origins:
            for origin in settings.cors_origins.split(","):
                clean = origin.strip().rstrip("/")
                if clean:
                    cors_allowed.add(clean)
        origins_list = list(cors_allowed) if cors_allowed else ["*"]
        origin_regex = r"^https:\/\/.*\.vercel\.app$"
    else:
        origins_list = ["*"]
        origin_regex = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins_list,
        allow_origin_regex=origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Error handlers ────────────────────────────────────────────────────────
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router, tags=["Health"])
    app.include_router(auth.router, prefix="/auth", tags=["Auth"])
    app.include_router(users.router, prefix="/users", tags=["Users"])
    app.include_router(groups.router, prefix="/groups", tags=["Groups"])
    app.include_router(invitations.router, prefix="/groups", tags=["Invitations"])
    app.include_router(invitations.router, prefix="/invitations", tags=["Invitations"])
    app.include_router(expenses.router, prefix="/groups", tags=["Expenses"])
    app.include_router(ledger.router, prefix="/groups", tags=["Ledger"])
    app.include_router(ai.router, prefix="/groups", tags=["AI"])

    return app


# Module-level app instance — uvicorn loads this
app = create_app()
