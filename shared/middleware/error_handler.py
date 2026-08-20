"""
shared/middleware/error_handler.py
────────────────────────────────────
FastAPI exception handlers that convert domain errors to HTTP responses.

Why middleware and not try/except in every route?
  DRY — without this, every route handler would need identical error-catching
  boilerplate. Centralising it means the mapping is in one place, and adding
  a new AppError subclass automatically inherits correct HTTP handling.
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from shared.errors import AppError

logger = logging.getLogger(__name__)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle all AppError subclasses → structured JSON error response."""
    if exc.status_code >= 500:
        logger.error(
            "Server error [%s] on %s %s: %s",
            exc.status_code,
            request.method,
            request.url.path,
            exc.message,
            exc_info=exc,
        )
    else:
        logger.warning(
            "Client error [%s] on %s %s: %s",
            exc.status_code,
            request.method,
            request.url.path,
            exc.message,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for unhandled exceptions.
    Returns a generic 500 without leaking internal details to the client.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again.",
        },
    )
