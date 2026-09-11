from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from modules.group.models import GroupMemberORM, GroupORM
from shared.errors import NotFoundError


class GroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_group(self, group: GroupORM) -> GroupORM:
        self._session.add(group)
        await self._session.flush()
        return group

    async def add_member(self, member: GroupMemberORM) -> GroupMemberORM:
        self._session.add(member)
        await self._session.flush()
        return member

    async def get_by_id(self, group_id: str) -> GroupORM | None:
        stmt = (
            select(GroupORM)
            .where(GroupORM.id == group_id)
            .options(selectinload(GroupORM.members).joinedload(GroupMemberORM.user))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, group_id: str) -> GroupORM:
        group = await self.get_by_id(group_id)
        if not group:
            raise NotFoundError("Group", group_id)
        return group

    async def is_member(self, group_id: str, user_id: str) -> bool:
        stmt = (
            select(GroupMemberORM.id)
            .where(
                GroupMemberORM.group_id == group_id,
                GroupMemberORM.user_id == user_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def get_member(self, group_id: str, user_id: str) -> GroupMemberORM | None:
        stmt = select(GroupMemberORM).where(
            GroupMemberORM.group_id == group_id,
            GroupMemberORM.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def remove_member(self, group_id: str, user_id: str) -> None:
        stmt = delete(GroupMemberORM).where(
            GroupMemberORM.group_id == group_id,
            GroupMemberORM.user_id == user_id,
        )
        await self._session.execute(stmt)
        await self._session.flush()
