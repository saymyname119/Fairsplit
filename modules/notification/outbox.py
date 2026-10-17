"""Transactional notification queue. Claims roll back on worker failure.

Delivery inserts a durable in-app notification in the same transaction as the
queue acknowledgement. Multiple workers use SKIP LOCKED; a crash releases locks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

logger = logging.getLogger(__name__)


class NotificationJobORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notification_jobs"
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_groups.id"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_accounts.id"))
    title: Mapped[str] = mapped_column(String(100))
    body: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class NotificationORM(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("notification_jobs.id"), unique=True)
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("group_groups.id"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_accounts.id"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    body: Mapped[str] = mapped_column(Text)


def enqueue(session, group_id: str, title: str, user_id: str, body: str) -> None:
    session.add(NotificationJobORM(group_id=group_id, user_id=user_id, title=title, body=body))


async def process_batch(session) -> int:
    result = await session.execute(
        select(NotificationJobORM)
        .where(
            NotificationJobORM.completed_at.is_(None),
            NotificationJobORM.available_at <= datetime.now(UTC),
        )
        .order_by(NotificationJobORM.created_at)
        .limit(50)
        .with_for_update(skip_locked=True)
    )
    jobs = result.scalars().all()
    for job in jobs:
        try:
            async with session.begin_nested():
                session.add(
                    NotificationORM(
                        job_id=job.id,
                        group_id=job.group_id,
                        user_id=job.user_id,
                        title=job.title,
                        body=job.body,
                    )
                )
                await session.flush()
            job.completed_at = datetime.now(UTC)
            job.last_error = None
        except Exception as exc:
            job.attempts += 1
            job.last_error = str(exc)[:2000]
            job.available_at = datetime.now(UTC) + timedelta(
                seconds=min(300, 2 ** min(job.attempts, 8))
            )
            logger.exception("Notification job %s failed; retry scheduled", job.id)
    await session.commit()
    return len(jobs)


async def run_worker() -> None:
    from shared.db.session import AsyncSessionFactory

    while True:
        try:
            async with AsyncSessionFactory() as session:
                await process_batch(session)
        except Exception:
            logger.exception("Notification worker failed; retrying")
        await asyncio.sleep(2)
