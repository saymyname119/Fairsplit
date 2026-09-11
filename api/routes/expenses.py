"""api/routes/expenses.py — Expense endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_dependency import get_current_user
from modules.expense import CreateExpenseRequest, Expense, ExpenseService
from shared.db.session import get_db

router = APIRouter()


@router.post(
    "/{group_id}/expenses",
    summary="Create an expense",
    status_code=201,
    response_model=Expense,
    responses={
        201: {"description": "Expense created, splits calculated, balances updated"},
        400: {"description": "Invalid expense data"},
        404: {"description": "Group or participant not found"},
        422: {"description": "Split amounts do not sum to total"},
    },
)
async def create_expense(
    group_id: str,
    request: CreateExpenseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Expense:
    """POST /groups/:id/expenses"""
    service = ExpenseService(db)
    return await service.create_expense(group_id, request)


@router.get(
    "/{group_id}/expenses",
    summary="List expenses for a group",
    response_model=list[Expense],
    responses={
        200: {"description": "Paginated list of expenses"},
        404: {"description": "Group not found"},
    },
)
async def list_expenses(
    group_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[Expense]:
    """GET /groups/:id/expenses — paginated, newest first."""
    service = ExpenseService(db)
    return await service.list_expenses(group_id, limit, offset)


@router.get(
    "/{group_id}/expenses/{expense_id}",
    summary="Get a single expense",
    response_model=Expense,
    responses={
        200: {"description": "Expense with splits"},
        404: {"description": "Expense not found"},
    },
)
async def get_expense(
    group_id: str,
    expense_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Expense:
    """GET /groups/:id/expenses/:expense_id"""
    service = ExpenseService(db)
    return await service.get_expense(expense_id)


@router.delete(
    "/{group_id}/expenses/{expense_id}",
    summary="Delete (soft) an expense",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Expense deleted"},
        403: {"description": "Not authorized to delete this expense"},
        404: {"description": "Expense not found"},
    },
)
async def delete_expense(
    group_id: str,
    expense_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """DELETE /groups/:id/expenses/:id"""
    service = ExpenseService(db)
    await service.delete_expense(expense_id, current_user["user_id"])
