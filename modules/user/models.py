"""
modules/user/models.py
───────────────────────
Domain models for the User module.

Two kinds of models here:
1. ORM model (UserORM) — maps to the `user_accounts` table. Only used inside
   this module's repository. Other modules NEVER see the ORM model.
2. Domain model (User) — a pure Pydantic model (no DB dependency). This is
   what the UserService returns and what other modules consume via the facade.

Why separate ORM and domain models?
  Layered architecture: the domain model is the module's *public contract*.
  If we change the DB schema (e.g., rename a column), only the ORM model and
  the repository change — the rest of the system is unaffected.
  This is especially important when splitting into microservices: the domain
  model becomes the DTO sent over the wire; the ORM model is private to the service.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# ─────────────────────────────────────────────────────────────────────────────
# ORM Model — private to this module, never imported by other modules
# ─────────────────────────────────────────────────────────────────────────────

class UserORM(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Database table: user_accounts
    Table is prefixed `user_` to namespace it within the shared schema.
    When this becomes a microservice, this table moves to its own DB.
    """

    __tablename__ = "user_accounts"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# ─────────────────────────────────────────────────────────────────────────────
# Domain / DTO Models — public, returned by the service facade
# ─────────────────────────────────────────────────────────────────────────────

class User(BaseModel):
    """Public domain representation of a user. No passwords, no internals."""

    id: str
    email: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # allows .model_validate(orm_instance)


class CreateUserRequest(BaseModel):
    """Input schema for user registration."""

    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UpdateUserRequest(BaseModel):
    """Partial update — all fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Input schema for authentication."""

    email: EmailStr
    password: str


class AuthTokens(BaseModel):
    """Returned upon successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Input for refreshing access token."""

    refresh_token: str
