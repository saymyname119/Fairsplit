"""
tests/integration/test_health.py — Integration test for /healthz endpoint.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


class TestHealthEndpoint:
    def test_health_returns_200_when_dependencies_ok(self, client):
        """
        Integration test: /healthz returns 200 when DB and Redis are reachable.
        We mock both connectivity checks so this test doesn't need real infrastructure.
        """
        with (
            patch(
                "api.routes.health.check_db_connection", new_callable=AsyncMock, return_value=True
            ),
            patch("redis.asyncio.Redis.ping", new_callable=AsyncMock, return_value=True),
        ):
            response = client.get("/healthz")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["services"]["database"] == "ok"

    def test_health_returns_503_when_db_down(self, client):
        with (
            patch(
                "api.routes.health.check_db_connection",
                new_callable=AsyncMock,
                return_value=False,
            ),
        ):
            response = client.get("/healthz")

        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "error"
        assert body["services"]["database"] == "error"

    def test_health_returns_200_degraded_when_redis_down(self, client):
        with (
            patch(
                "api.routes.health.check_db_connection", new_callable=AsyncMock, return_value=True
            ),
            patch(
                "redis.asyncio.Redis.ping",
                new_callable=AsyncMock,
                side_effect=Exception("Redis down"),
            ),
        ):
            response = client.get("/healthz")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "degraded"
        assert body["services"]["database"] == "ok"
        assert body["services"]["redis"] == "error"

