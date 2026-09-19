"""
tests/conftest.py
──────────────────
Shared pytest fixtures for unit and integration tests.

Fixture scopes:
  session  → created once for the entire test run (DB engine, settings override)
  function → created fresh for each test (event bus, DB session)

Why reset_event_bus() in each test?
  The event bus is a module-level singleton. If test A subscribes a handler,
  it would persist into test B. reset_event_bus() ensures handler isolation.
"""

from __future__ import annotations

import os

import pytest

# Override settings BEFORE importing the app
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["CLAUDE_API_KEY"] = "not-a-real-key"

from shared.config import get_settings
get_settings.cache_clear()

from collections.abc import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient  # noqa: E402

from api.app import create_app  # noqa: E402
from shared.events import reset_event_bus  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_event_bus() -> Generator[None, None, None]:
    """Reset event bus before each test to prevent handler leakage."""
    reset_event_bus()
    yield
    reset_event_bus()


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create a single FastAPI app instance for the test session."""
    return create_app()


@pytest.fixture(scope="session")
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """
    TestClient wraps the FastAPI app for HTTP testing.
    scope=session: one client for all tests (cheaper than creating per test).
    """
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
