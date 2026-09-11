"""tests/unit/test_cache.py — Redis cache helper tests (mocked Redis)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from shared.cache import balance_cache_key, get_cached, invalidate, set_cached


@pytest.fixture(autouse=True)
def mock_redis():
    """Mock the Redis client for all tests in this file."""
    mock_r = AsyncMock()
    with patch("shared.cache.get_redis", return_value=mock_r):
        yield mock_r


@pytest.mark.asyncio
async def test_get_cached_hit(mock_redis):
    mock_redis.get.return_value = json.dumps([{"creditor_id": "a", "debtor_id": "b"}])
    result = await get_cached("balances:group:g1")
    assert result is not None
    data = json.loads(result)
    assert data[0]["creditor_id"] == "a"


@pytest.mark.asyncio
async def test_get_cached_miss(mock_redis):
    mock_redis.get.return_value = None
    result = await get_cached("balances:group:g1")
    assert result is None


@pytest.mark.asyncio
async def test_set_cached_calls_redis_set(mock_redis):
    await set_cached("balances:group:g1", [{"test": "data"}], ttl=60)
    mock_redis.set.assert_called_once()
    args = mock_redis.set.call_args
    assert args[0][0] == "balances:group:g1"
    assert json.loads(args[0][1]) == [{"test": "data"}]
    assert args[1]["ex"] == 60


@pytest.mark.asyncio
async def test_invalidate_calls_redis_delete(mock_redis):
    await invalidate("balances:group:g1")
    mock_redis.delete.assert_called_once_with("balances:group:g1")


@pytest.mark.asyncio
async def test_get_cached_redis_down_returns_none(mock_redis):
    """Fail-open: if Redis is down, get_cached returns None (not an exception)."""
    mock_redis.get.side_effect = ConnectionError("Redis unavailable")
    result = await get_cached("balances:group:g1")
    assert result is None


@pytest.mark.asyncio
async def test_set_cached_redis_down_no_exception(mock_redis):
    """Fail-open: if Redis is down, set_cached doesn't raise."""
    mock_redis.set.side_effect = ConnectionError("Redis unavailable")
    # Should not raise
    await set_cached("balances:group:g1", [{"test": "data"}])


@pytest.mark.asyncio
async def test_invalidate_redis_down_no_exception(mock_redis):
    """Fail-open: if Redis is down, invalidate doesn't raise."""
    mock_redis.delete.side_effect = ConnectionError("Redis unavailable")
    # Should not raise
    await invalidate("balances:group:g1")


def test_balance_cache_key_format():
    key = balance_cache_key("group-abc-123")
    assert key == "balances:group:group-abc-123"
