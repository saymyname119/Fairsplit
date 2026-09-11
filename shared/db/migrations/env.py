"""
shared/db/migrations/env.py
────────────────────────────
Alembic environment configuration.

Key points:
- Uses synchronous psycopg2 driver for migrations (Alembic doesn't support asyncpg).
- DATABASE_URL env var overrides alembic.ini sqlalchemy.url.
- target_metadata imports ALL ORM models so autogenerate detects all tables.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from modules.expense.models import ExpenseORM, SplitORM  # noqa: F401
from modules.group.models import GroupMemberORM, GroupORM  # noqa: F401
from modules.ledger.models import LedgerBalanceORM, SettlementORM  # noqa: F401

# Import all ORM models so their tables appear in metadata
from modules.user.models import UserORM  # noqa: F401

# Must import all ORM models before accessing Base.metadata
# so Alembic autogenerate can see all tables.
# Order matters: import Base first, then all models.
from shared.db.base import Base  # noqa: F401 — side effect: registers Base.metadata

from shared.config import get_settings

config = context.config

settings = get_settings()
database_url = os.getenv("DATABASE_URL", settings.database_url)
if database_url and "asyncpg" in database_url:
    database_url = database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to DB and apply)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
