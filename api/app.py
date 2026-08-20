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

from api.routes import ai, auth, expenses, groups, health, ledger, users
from modules.notification import register_notification_handlers
from shared.config import get_settings
from shared.db.session import check_db_connection
from shared.errors import AppError
from shared.events import get_event_bus
from shared.middleware.error_handler import app_error_handler, unhandled_exception_handler

logger = logging.getLogger(__name__)
settings = get_settings()


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
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
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
    app.include_router(expenses.router, prefix="/groups", tags=["Expenses"])
    app.include_router(ledger.router, prefix="/groups", tags=["Ledger"])
    app.include_router(ai.router, prefix="/groups", tags=["AI"])

    return app


# Module-level app instance — uvicorn loads this
app = create_app()
