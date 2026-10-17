"""Authenticated, member-scoped AI expense previews. Never creates expenses."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth_dependency import get_current_user
from api.routes.ledger import require_member
from modules.ai.models import ParseExpenseRequest, ParseExpenseResponse
from modules.ai.service import AiService
from modules.group.service import GroupService
from shared.db.session import get_db

router = APIRouter(dependencies=[Depends(require_member)])


@router.post("/{group_id}/expenses/parse", response_model=ParseExpenseResponse)
async def parse_expense(
    group_id: str,
    request: ParseExpenseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    group = await GroupService(db).get_group(group_id)
    return await AiService().parse_expense(
        request, group.members, current_user["user_id"], group.currency
    )
