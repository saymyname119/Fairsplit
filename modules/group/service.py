from __future__ import annotations

import abc

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from modules.group.models import (
    AddMemberRequest,
    CreateGroupRequest,
    Group,
    GroupMember,
    GroupMemberORM,
    GroupORM,
    MemberRole,
)
from modules.group.repository import GroupRepository
from shared.errors import ConflictError, ForbiddenError
from shared.events import GroupCreated, MemberAdded, get_event_bus


class IGroupService(abc.ABC):
    @abc.abstractmethod
    async def create_group(self, creator_id: str, request: CreateGroupRequest) -> Group: ...

    @abc.abstractmethod
    async def add_member(
        self, group_id: str, adder_id: str, request: AddMemberRequest
    ) -> Group: ...


class GroupService(IGroupService):
    def __init__(self, session: AsyncSession) -> None:
        self._repo = GroupRepository(session)
        self._bus = get_event_bus()

    async def create_group(self, creator_id: str, request: CreateGroupRequest) -> Group:
        orm_group = GroupORM(
            name=request.name,
            description=request.description,
            created_by_id=creator_id,
        )
        await self._repo.create_group(orm_group)

        # Creator is automatically an admin member
        orm_member = GroupMemberORM(
            group_id=orm_group.id,
            user_id=creator_id,
            role=MemberRole.ADMIN,
        )
        await self._repo.add_member(orm_member)

        # We need to re-fetch to load relationships properly for the domain model
        loaded_group = await self._repo.get_by_id_or_raise(orm_group.id)
        domain_group = self._map_to_domain(loaded_group)

        self._bus.publish(
            GroupCreated(
                group_id=domain_group.id,
                name=domain_group.name,
                creator_id=creator_id,
            )
        )
        return domain_group

    async def add_member(self, group_id: str, adder_id: str, request: AddMemberRequest) -> Group:
        await self._repo.get_by_id_or_raise(group_id)

        # Ensure the adder is an admin
        adder_member = await self._repo.get_member(group_id, adder_id)
        if not adder_member or adder_member.role != MemberRole.ADMIN:
            raise ForbiddenError("Only admins can add members")

        orm_member = GroupMemberORM(
            group_id=group_id,
            user_id=request.user_id,
            role=request.role,
        )

        try:
            await self._repo.add_member(orm_member)
        except IntegrityError as err:
            # Foreign key violation (user doesn't exist) or unique violation
            raise ConflictError("User is already a member or does not exist") from err

        loaded_group = await self._repo.get_by_id_or_raise(group_id)
        domain_group = self._map_to_domain(loaded_group)

        self._bus.publish(
            MemberAdded(
                group_id=group_id,
                user_id=request.user_id,
                added_by_id=adder_id,
            )
        )
        return domain_group

    def _map_to_domain(self, orm_group: GroupORM) -> Group:
        members = []
        for m in orm_group.members:
            # Safely get user info (requires eager loading)
            user_name = m.user.name if getattr(m, "user", None) else "Unknown"
            user_email = m.user.email if getattr(m, "user", None) else "Unknown"

            members.append(
                GroupMember(
                    user_id=m.user_id,
                    user_name=user_name,
                    user_email=user_email,
                    role=MemberRole(m.role),
                    joined_at=m.created_at,
                )
            )

        return Group(
            id=orm_group.id,
            name=orm_group.name,
            description=orm_group.description,
            created_by_id=orm_group.created_by_id,
            created_at=orm_group.created_at,
            members=members,
        )
