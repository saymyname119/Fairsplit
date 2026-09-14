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
    "isolated_transaction",
]


def __getattr__(name: str) -> Any:
    lazy_exports = {
        "engine",
        "AsyncSessionFactory",
        "get_db",
        "check_db_connection",
        "isolated_transaction",
    }
    if name in lazy_exports:
        from shared.db.session import (
            AsyncSessionFactory,
            check_db_connection,
            engine,
            get_db,
            isolated_transaction,
        )

        return {
            "engine": engine,
            "AsyncSessionFactory": AsyncSessionFactory,
            "get_db": get_db,
            "check_db_connection": check_db_connection,
            "isolated_transaction": isolated_transaction,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

