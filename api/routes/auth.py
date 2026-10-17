from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from modules.user import AuthTokens, LoginRequest, RefreshTokenRequest, User, UserService
from modules.user.identity import verified_supabase_user
from modules.user.recovery import request_reset, reset_password
from shared.db.session import get_db

router = APIRouter()


class OAuthSyncResponse(BaseModel):
    user: User
    tokens: AuthTokens


@router.post("/oauth-sync", response_model=OAuthSyncResponse)
async def oauth_sync(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: AsyncSession = Depends(get_db),
) -> OAuthSyncResponse:
    """
    Sync an OAuth user (Google / Supabase) into the local database
    and return FastAPI JWT tokens.
    """
    identity = await verified_supabase_user(credentials.credentials)
    service = UserService(db)
    metadata = identity.get("user_metadata") or {}
    user, tokens = await service.sync_oauth_user(
        identity["email"],
        metadata.get("full_name") or metadata.get("name") or identity["email"].split("@")[0],
    )
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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=8, max_length=72)


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    await request_reset(db, request.email)
    return {"message": "If an active account exists, a password reset link has been sent."}


@router.post("/reset-password")
async def complete_password_reset(
    request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    await reset_password(db, request.token, request.password)
    return {"message": "Password updated. Sign in with your new password."}
