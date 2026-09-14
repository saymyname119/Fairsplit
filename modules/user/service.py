from __future__ import annotations

import abc
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from modules.user.models import (
    AuthTokens,
    CreateUserRequest,
    LoginRequest,
    RefreshTokenRequest,
    User,
    UserORM,
)
from modules.user.repository import UserRepository
from shared.config import get_settings
from shared.errors import AuthenticationError, ConflictError


class IUserService(abc.ABC):
    """Facade for the User module."""

    @abc.abstractmethod
    async def create_user(self, request: CreateUserRequest) -> User: ...

    @abc.abstractmethod
    async def authenticate(self, request: LoginRequest) -> AuthTokens: ...

    @abc.abstractmethod
    async def refresh_token(self, request: RefreshTokenRequest) -> AuthTokens: ...

    @abc.abstractmethod
    async def get_user(self, user_id: str) -> User: ...

    @abc.abstractmethod
    async def sync_oauth_user(
        self, email: str, name: str, avatar_url: str | None = None
    ) -> tuple[User, AuthTokens]: ...


class UserService(IUserService):
    """Implementation of User module business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)
        self._settings = get_settings()

    async def create_user(self, request: CreateUserRequest) -> User:
        if await self._repo.exists_by_email(request.email):
            raise ConflictError("Email already exists")

        hashed_bytes = bcrypt.hashpw(request.password.encode("utf-8"), bcrypt.gensalt())
        hashed = hashed_bytes.decode("utf-8")
        orm_user = UserORM(
            email=request.email,
            name=request.name,
            hashed_password=hashed,
        )
        try:
            created = await self._repo.create(orm_user)
            return User.model_validate(created)
        except IntegrityError as err:
            raise ConflictError("Email already exists") from err

    async def authenticate(self, request: LoginRequest) -> AuthTokens:
        user = await self._repo.get_by_email(request.email)
        if not user or not bcrypt.checkpw(
            request.password.encode("utf-8"), user.hashed_password.encode("utf-8")
        ):
            # Same error for not found and wrong password (no user enum)
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("User account is disabled")

        return self._generate_tokens(user.id, user.email)

    async def refresh_token(self, request: RefreshTokenRequest) -> AuthTokens:
        try:
            payload = jwt.decode(
                request.refresh_token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
            )
            token_type = payload.get("type")
            if token_type != "refresh":
                raise AuthenticationError("Invalid token type")

            user_id = payload.get("sub")
            email = payload.get("email")
            if not user_id or not email:
                raise AuthenticationError("Invalid token payload")

            return self._generate_tokens(user_id, email)
        except JWTError as err:
            raise AuthenticationError("Invalid or expired refresh token") from err

    async def get_user(self, user_id: str) -> User:
        orm_user = await self._repo.get_by_id_or_raise(user_id)
        return User.model_validate(orm_user)

    async def sync_oauth_user(
        self, email: str, name: str, avatar_url: str | None = None
    ) -> tuple[User, AuthTokens]:
        """Sync an OAuth authenticated user (Google / Supabase) into local user_accounts."""
        user = await self._repo.get_by_email(email)
        if not user:
            import secrets

            rand_pw = secrets.token_urlsafe(32)
            hashed = bcrypt.hashpw(rand_pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            orm_user = UserORM(
                email=email,
                name=name or email.split("@")[0],
                hashed_password=hashed,
            )
            user = await self._repo.create(orm_user)
        elif name and user.name != name:
            # Update name if changed
            user.name = name
            await self._repo.update(user)

        tokens = self._generate_tokens(user.id, user.email)
        return User.model_validate(user), tokens

    def _generate_tokens(self, user_id: str, email: str) -> AuthTokens:
        now = datetime.now(UTC)

        access_exp = now + timedelta(minutes=self._settings.jwt_expiry_minutes)
        access_payload = {
            "sub": user_id,
            "email": email,
            "exp": access_exp,
            "type": "access",
        }
        access_token = jwt.encode(
            access_payload, self._settings.jwt_secret, algorithm=self._settings.jwt_algorithm
        )

        refresh_exp = now + timedelta(days=7)  # Hardcoded 7 days for refresh
        refresh_payload = {
            "sub": user_id,
            "email": email,
            "exp": refresh_exp,
            "type": "refresh",
        }
        refresh_token = jwt.encode(
            refresh_payload, self._settings.jwt_secret, algorithm=self._settings.jwt_algorithm
        )

        return AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self._settings.jwt_expiry_minutes * 60,
        )
