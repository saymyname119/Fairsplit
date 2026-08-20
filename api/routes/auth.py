from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from modules.user import AuthTokens, LoginRequest, RefreshTokenRequest, UserService
from shared.db.session import get_db

router = APIRouter()


@router.post("/login", response_model=AuthTokens)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthTokens:
    """Authenticate and get access/refresh tokens."""
    service = UserService(db)
    return await service.authenticate(request)


@router.post("/refresh", response_model=AuthTokens)
async def refresh(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthTokens:
    """Refresh access token using a valid refresh token."""
    service = UserService(db)
    return await service.refresh_token(request)
