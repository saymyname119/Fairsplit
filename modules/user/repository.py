from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.user.models import UserORM
from shared.errors import NotFoundError


class UserRepository:
    """
    Repository for user_accounts table.
    Encapsulates all SQLAlchemy queries for the User module.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user: UserORM) -> UserORM:
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: str) -> UserORM | None:
        return await self._session.get(UserORM, user_id)

    async def get_by_id_or_raise(self, user_id: str) -> UserORM:
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)
        return user

    async def get_by_email(self, email: str) -> UserORM | None:
        stmt = select(UserORM).where(UserORM.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        stmt = select(UserORM.id).where(UserORM.email == email).limit(1)
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def update(self, user: UserORM) -> UserORM:
        self._session.add(user)
        await self._session.flush()
        return user

