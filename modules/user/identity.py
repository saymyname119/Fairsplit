"""Verify Supabase identity with the configured Auth server, never browser claims."""

import httpx

from shared.config import get_settings
from shared.errors import AuthenticationError, ExternalServiceError


async def verified_supabase_user(token: str) -> dict:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise ExternalServiceError("Google sign-in is not configured on the server")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                settings.supabase_url.rstrip("/") + "/auth/v1/user",
                headers={
                    "apikey": settings.supabase_publishable_key,
                    "Authorization": "Bearer " + token,
                },
            )
        if response.status_code in (401, 403):
            raise AuthenticationError("Invalid or expired Google session. Please sign in again.")
        response.raise_for_status()
        user = response.json()
        if not user.get("id") or not user.get("email") or not user.get("email_confirmed_at"):
            raise AuthenticationError("A verified email is required")
        return user
    except (httpx.HTTPError, ValueError) as exc:
        raise ExternalServiceError("Unable to verify Google sign-in. Please try again.") from exc
