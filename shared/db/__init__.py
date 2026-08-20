"""shared/db/__init__.py"""

from __future__ import annotations

from typing import Any

from shared.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

__all__ = [
    "Base",
    "UUIDPrimaryKeyMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "engine",
    "AsyncSessionFactory",
    "get_db",
    "check_db_connection",
]


def __getattr__(name: str) -> Any:
    if name in {"engine", "AsyncSessionFactory", "get_db", "check_db_connection"}:
        from shared.db.session import AsyncSessionFactory, check_db_connection, engine, get_db

        return {
            "engine": engine,
            "AsyncSessionFactory": AsyncSessionFactory,
            "get_db": get_db,
            "check_db_connection": check_db_connection,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
