"""api/routes/expenses.py — Expense endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
    db: AsyncSession = Depends(get_db)
) -> Expense:
    """POST /groups/:id/expenses"""
    service = ExpenseService(db)
    return await service.create_expense(group_id, request)


@router.get(
    "/{group_id}/expenses",
    summary="List expenses for a group",
    responses={
        200: {"description": "Paginated list of expenses"},
        404: {"description": "Group not found"},
    },
)
async def list_expenses(
    group_id: str,
    limit: int = 50,
    offset: int = 0,
) -> JSONResponse:
    """GET /groups/:id/expenses — full implementation in Prompt 3."""
    return JSONResponse(status_code=501, content={"message": "Coming in Prompt 3"})


@router.get(
    "/{group_id}/expenses/{expense_id}",
    summary="Get a single expense",
    responses={
        200: {"description": "Expense with splits"},
        404: {"description": "Expense not found"},
    },
)
async def get_expense(group_id: str, expense_id: str) -> JSONResponse:
    """GET /groups/:id/expenses/:expense_id — full implementation in Prompt 3."""
    return JSONResponse(status_code=501, content={"message": "Coming in Prompt 3"})


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
    db: AsyncSession = Depends(get_db)
) -> None:
    """DELETE /groups/:id/expenses/:id"""
    deleter_id = "temp-deleter-id" # Will be replaced with auth token payload
    service = ExpenseService(db)
    await service.delete_expense(expense_id, deleter_id)
