"""
shared/cache.py
────────────────
Redis cache helpers for the balance caching layer.

Caching strategy: Write-Invalidate
───────────────────────────────────
When an expense is created or a settlement is recorded, we DELETE the cached
balance for that group (invalidation). The next read recalculates from DB and
re-caches.

Why not write-through (update cache on write)?
  1. Money data: a stale cache means showing a WRONG balance. Invalidation
     guarantees the next read is fresh from DB — write-through could fail
     silently (e.g., the cache update succeeds but DB transaction rolls back).
  2. Simplicity: invalidation is one `DELETE key` operation. Write-through
     requires serializing the new balance and atomically updating the cache,
     which is more complex and more likely to have bugs.

TTL as a safety net:
  We set a TTL (default: 300 seconds) on cached balances. This means even if
  an invalidation event is lost (process crash, event bus failure), the stale
  cache will self-expire within 5 minutes. The TTL is NOT the primary freshness
  mechanism — invalidation is.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from shared.config import get_settings

logger = logging.getLogger(__name__)

# ── Redis client singleton ────────────────────────────────────────────────────
_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return the application-wide Redis client singleton."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
        )
    return _redis


async def close_redis() -> None:
    """Close the Redis connection. Called at app shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


# ── Cache operations ──────────────────────────────────────────────────────────


async def get_cached(key: str) -> str | None:
    """
    Get a cached value by key.
    Returns None on cache miss or Redis connection error (fail-open).
    """
    try:
        r = get_redis()
        value = await r.get(key)
        if value is not None:
            logger.debug("Cache HIT: %s", key)
        else:
            logger.debug("Cache MISS: %s", key)
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value
    except Exception:
        # Fail-open: if Redis is down, the app still works (just slower)
        logger.warning("Redis get failed for key %s — falling through to DB", key)
        return None


async def set_cached(key: str, value: Any, ttl: int | None = None) -> None:
    """
    Set a cached value with optional TTL (seconds).
    If ttl is None, uses the configured balance_cache_ttl_seconds.
    Silently fails on Redis errors (fail-open).
    """
    try:
        if ttl is None:
            ttl = get_settings().balance_cache_ttl_seconds
        r = get_redis()
        serialized = json.dumps(value, default=str)
        await r.set(key, serialized, ex=ttl)
        logger.debug("Cache SET: %s (TTL=%ds)", key, ttl)
    except Exception:
        logger.warning("Redis set failed for key %s — proceeding without cache", key)


async def invalidate(key: str) -> None:
    """
    Delete a cached key. Used by event handlers on ExpenseCreated / SettlementRecorded.
    Silently fails on Redis errors.
    """
    try:
        r = get_redis()
        await r.delete(key)
        logger.info("Cache INVALIDATED: %s", key)
    except Exception:
        logger.warning("Redis invalidate failed for key %s", key)


def balance_cache_key(group_id: str) -> str:
    """Generate the canonical cache key for a group's balances."""
    return f"balances:group:{group_id}"
