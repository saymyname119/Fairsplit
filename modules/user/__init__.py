"""modules/user/__init__.py — public interface for the user module."""

from modules.user.models import (
    AuthTokens,
    CreateUserRequest,
    LoginRequest,
    RefreshTokenRequest,
    UpdateUserRequest,
    User,
)
from modules.user.service import IUserService, UserService

__all__ = [
    # Domain models (public)
    "User",
    "CreateUserRequest",
    "UpdateUserRequest",
    "LoginRequest",
    "AuthTokens",
    "RefreshTokenRequest",
    # Service interface + implementation
    "IUserService",
    "UserService",
]

# ────────────────────────────────────────────────────────────────────────────
# What is NOT exported here (private to this module):
#   - UserORM          (DB model — internal to repository layer)
#   - UserRepository   (DB access — internal, swapped out in tests)
#   - hashed_password  (never leaves this module)
# ────────────────────────────────────────────────────────────────────────────
