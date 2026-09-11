"""api/routes/users.py — User endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_dependency import get_current_user
from modules.ledger import LedgerService, UserBalance
from modules.user import CreateUserRequest, User, UserService
from shared.db.session import get_db

router = APIRouter()


@router.post(
    "/",
    summary="Register a new user",
    status_code=201,
    response_model=User,
    responses={
        201: {"description": "User created"},
        400: {"description": "Email already taken or invalid input"},
        409: {"description": "Email already exists"},
    },
)
async def create_user(request: CreateUserRequest, db: AsyncSession = Depends(get_db)) -> User:
    """
    POST /users
    Register a new user account.
    Note: Registration does NOT require authentication (public endpoint).
    """
    service = UserService(db)
    return await service.create_user(request)


@router.get(
    "/{user_id}",
    summary="Get user profile",
    response_model=User,
    responses={
        200: {"description": "User profile"},
        404: {"description": "User not found"},
    },
)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> User:
    """GET /users/:id — return user profile."""
    service = UserService(db)
    return await service.get_user(user_id)


@router.get(
    "/{user_id}/balances",
    summary="Get a user's balances across all groups",
    response_model=UserBalance,
    responses={
        200: {"description": "Aggregated balance across all groups"},
        404: {"description": "User not found"},
    },
)
async def get_user_balances(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserBalance:
    """
    GET /users/:id/balances
    Returns aggregated balance across all groups the user belongs to.
    """
    service = LedgerService(db)
    return await service.get_user_balances(user_id)
