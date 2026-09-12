"""api/routes/health.py — GET /healthz endpoint."""

from __future__ import annotations

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from shared.config import get_settings
from shared.db.session import check_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


@router.get(
    "/healthz",
    summary="Health check",
    description="Returns application health including DB and Redis connectivity.",
    response_description="Health status object",
)
async def healthz() -> JSONResponse:
    """
    Kubernetes/Docker health probe endpoint.
    Returns 200 if all dependencies are reachable, 503 otherwise.
    Useful for load balancer health checks in production.
    """
    db_ok = await check_db_connection()

    # Check Redis connectivity (short timeout — don't block health probes)
    redis_ok = False
    try:
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=1)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        logger.warning("Redis health check failed")

    # DB is the critical service — return 200 if DB is OK (even without Redis)
    if db_ok:
        status = "ok" if redis_ok else "degraded"
        http_code = 200
    else:
        status = "error"
        http_code = 503

    return JSONResponse(
        status_code=http_code,
        content={
            "status": status,
            "services": {
                "database": "ok" if db_ok else "error",
                "redis": "ok" if redis_ok else "error",
            },
        },
    )
