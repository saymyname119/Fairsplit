from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from modules.user import AuthTokens, LoginRequest, RefreshTokenRequest, User, UserService
from shared.db.session import get_db

router = APIRouter()


class OAuthSyncRequest(BaseModel):
    email: EmailStr
    name: str
    avatar_url: str | None = None


class OAuthSyncResponse(BaseModel):
    user: User
    tokens: AuthTokens


@router.post("/oauth-sync", response_model=OAuthSyncResponse)
async def oauth_sync(
    request: OAuthSyncRequest,
    db: AsyncSession = Depends(get_db),
) -> OAuthSyncResponse:
    """
    Sync an OAuth user (Google / Supabase) into the local database
    and return FastAPI JWT tokens.
    """
    service = UserService(db)
    user, tokens = await service.sync_oauth_user(request.email, request.name, request.avatar_url)
    return OAuthSyncResponse(user=user, tokens=tokens)


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
