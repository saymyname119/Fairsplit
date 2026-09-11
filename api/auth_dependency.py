"""
api/auth_dependency.py
───────────────────────
Reusable FastAPI dependency for JWT-based authentication.

Usage in a route:
    from api.auth_dependency import get_current_user

    @router.post("/")
    async def create(current_user: dict = Depends(get_current_user)):
        user_id = current_user["user_id"]
        ...

Design notes:
  - Returns a plain dict (not a full User domain model) to avoid a DB round-trip
    on every authenticated request. The JWT payload already contains user_id and email.
  - If a route needs the full User object (rare), it can call UserService.get_user()
    with the user_id from the dict.
  - OAuth2PasswordBearer tells Swagger UI to show the "Authorize" button, making
    manual API testing easy.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from shared.config import get_settings
from shared.errors import AuthenticationError

# tokenUrl tells Swagger UI where to send the login request for the "Authorize" flow.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """
    Decode and validate the JWT bearer token.

    Returns
    -------
    dict with keys: user_id, email

    Raises
    ------
    AuthenticationError (401) if the token is missing, expired, or invalid.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        token_type = payload.get("type")
        if token_type != "access":
            raise AuthenticationError("Invalid token type — expected access token")

        user_id: str | None = payload.get("sub")
        email: str | None = payload.get("email")

        if not user_id or not email:
            raise AuthenticationError("Invalid token payload")

        return {"user_id": user_id, "email": email}

    except JWTError as err:
        raise AuthenticationError("Invalid or expired token") from err
