"""Feature flows on a disposable PostgreSQL database; never uses the app DB."""

import asyncio
import os
import uuid
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.app import create_app
from modules.user.models import CreateUserRequest, LoginRequest, RefreshTokenRequest
from modules.user.recovery import request_reset, reset_password
from modules.user.service import UserService
from shared.db.session import get_db
from shared.errors import AuthenticationError

pytestmark = pytest.mark.skipif(
    not os.getenv("FAIRSPLIT_TEST_DATABASE_URL"), reason="Requires disposable PostgreSQL"
)


async def test_currency_oauth_and_ai_api_flow():
    engine = create_async_engine(os.environ["FAIRSPLIT_TEST_DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app()

    async def database():
        async with factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    app.dependency_overrides[get_db] = database
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        unique = uuid.uuid4().hex
        users = []
        for name in ("Alex", "Sam"):
            response = await client.post(
                "/users/",
                json={
                    "name": name,
                    "email": f"{name}-{unique}@example.com",
                    "password": "test-password-123",
                },
            )
            assert response.status_code == 201, response.text
            users.append(response.json())
        login = await client.post(
            "/auth/login", json={"email": users[0]["email"], "password": "test-password-123"}
        )
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        group = await client.post(
            "/groups/", json={"name": "Currency regression", "currency": "INR"}, headers=headers
        )
        assert group.status_code == 201, group.text
        gid = group.json()["id"]
        await client.post(
            f"/groups/{gid}/members", json={"user_id": users[1]["id"]}, headers=headers
        )
        groups = await client.get("/groups/", headers=headers)
        assert next(g for g in groups.json() if g["id"] == gid)["currency"] == "INR"
        expense = await client.post(
            f"/groups/{gid}/expenses",
            json={
                "paid_by_id": users[0]["id"],
                "amount": "800",
                "description": "Dinner",
                "split_type": "equal",
                "participants": [u["id"] for u in users],
            },
            headers=headers,
        )
        assert expense.status_code == 201, expense.text
        assert expense.json()["currency"] == "INR"
        assert (await client.get(f"/groups/{gid}/expenses", headers=headers)).json()[0][
            "currency"
        ] == "INR"
        debts = await client.get(f"/groups/{gid}/balances/simplified", headers=headers)
        assert debts.json()["currency"] == "INR", debts.text
        # Sending an arbitrary email no longer signs anyone in.
        forged = await client.post(
            "/auth/oauth-sync", json={"email": users[0]["email"], "name": "Impostor"}
        )
        assert forged.status_code in (401, 403)
        # A server-verified identity is the only source for account synchronization.
        identity = {
            "id": "supabase-id",
            "email": users[0]["email"],
            "email_confirmed_at": "now",
            "user_metadata": {"full_name": "Alex"},
        }
        with patch("api.routes.auth.verified_supabase_user", AsyncMock(return_value=identity)):
            synced = await client.post(
                "/auth/oauth-sync",
                headers={"Authorization": "Bearer verified"},
                json={"email": "attacker@example.com"},
            )
        assert synced.status_code == 200, synced.text
        assert synced.json()["user"]["email"] == users[0]["email"]
        with patch("modules.ai.service.get_settings") as settings:
            settings.return_value.claude_api_key = ""
            unavailable = await client.post(
                f"/groups/{gid}/expenses/parse",
                headers=headers,
                json={"text": "Dinner 800 for Alex and Sam"},
            )
        assert unavailable.status_code == 502
        assert (
            await client.post(
                f"/groups/{gid}/expenses/parse", json={"text": "Dinner for Alex and Sam"}
            )
        ).status_code == 401
    await engine.dispose()


async def test_reset_is_single_use_and_revokes_existing_tokens():
    engine = create_async_engine(os.environ["FAIRSPLIT_TEST_DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    email = uuid.uuid4().hex + "@example.com"
    async with factory() as db:
        service = UserService(db)
        await service.create_user(
            CreateUserRequest(name="Recovery test", email=email, password="original-password")
        )
        old_tokens = await service.authenticate(
            LoginRequest(email=email, password="original-password")
        )
        await db.commit()
    sender = AsyncMock(return_value=True)
    with patch("modules.user.recovery.SmtpClient") as smtp:
        smtp.return_value.is_configured = True
        smtp.return_value.send_email = sender
        async with factory() as db:
            await request_reset(db, email)
            await db.commit()
    text = sender.call_args.kwargs["text"]
    token = parse_qs(urlparse(text.split(": ", 1)[1]).query)["reset_token"][0]

    async def consume():
        async with factory() as db:
            try:
                await reset_password(db, token, "replacement-password")
                await db.commit()
                return True
            except AuthenticationError:
                await db.rollback()
                return False

    assert sorted(await asyncio.gather(consume(), consume())) == [False, True]
    async with factory() as db:
        service = UserService(db)
        with pytest.raises(AuthenticationError):
            await service.authenticate(LoginRequest(email=email, password="original-password"))
        new = await service.authenticate(LoginRequest(email=email, password="replacement-password"))
        assert new.access_token
        with pytest.raises(AuthenticationError, match="Password changed"):
            await service.refresh_token(RefreshTokenRequest(refresh_token=old_tokens.refresh_token))
        from api.auth_dependency import get_current_user

        with pytest.raises(AuthenticationError, match="Password changed"):
            await get_current_user(old_tokens.access_token, db)
    await engine.dispose()
