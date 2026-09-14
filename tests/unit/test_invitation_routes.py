"""tests/unit/test_invitation_routes.py — HTTP endpoint tests for invitations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.auth_dependency import get_current_user
from modules.invitation import Invitation, InvitationInfo, InvitationStatus
from shared.db.session import get_db


@pytest.fixture
def auth_override(app):
    """Override get_current_user to return mock admin user."""
    async def _mock_user():
        return {"user_id": "usr-admin-1", "email": "admin@example.com"}

    async def _mock_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = _mock_user
    app.dependency_overrides[get_db] = _mock_db
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def test_create_invitation_endpoint(client: TestClient, auth_override):
    now = datetime.now(UTC)
    mock_inv = Invitation(
        id="inv_123",
        group_id="grp_1",
        group_name="Tokyo Foodies",
        invited_by_id="usr-admin-1",
        invited_by_name="Admin",
        email="friend@example.com",
        status=InvitationStatus.PENDING,
        created_at=now,
        expires_at=now + timedelta(days=7),
    )

    with patch(
        "modules.invitation.InvitationService.create_invitation",
        new_callable=AsyncMock,
        return_value=mock_inv,
    ):
        resp = client.post(
            "/groups/grp_1/invitations",
            json={"email": "friend@example.com"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "inv_123"
        assert data["email"] == "friend@example.com"
        assert data["group_name"] == "Tokyo Foodies"


def test_list_pending_invitations_endpoint(client: TestClient, auth_override):
    now = datetime.now(UTC)
    mock_inv = Invitation(
        id="inv_123",
        group_id="grp_1",
        group_name="Tokyo Foodies",
        invited_by_id="usr-admin-1",
        invited_by_name="Admin",
        email="friend@example.com",
        status=InvitationStatus.PENDING,
        created_at=now,
        expires_at=now + timedelta(days=7),
    )

    with patch(
        "modules.invitation.InvitationService.list_pending",
        new_callable=AsyncMock,
        return_value=[mock_inv],
    ):
        resp = client.get("/groups/grp_1/invitations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "inv_123"


def test_get_invitation_info_endpoint(client: TestClient, auth_override):
    mock_info = InvitationInfo(
        id="inv_123",
        group_name="Tokyo Foodies",
        invited_by_name="Admin",
        email="friend@example.com",
        status=InvitationStatus.PENDING,
        is_expired=False,
    )

    with patch(
        "modules.invitation.InvitationService.get_invitation_info",
        new_callable=AsyncMock,
        return_value=mock_info,
    ):
        resp = client.get("/invitations/info/tok_abc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_name"] == "Tokyo Foodies"
        assert data["is_expired"] is False


def test_accept_invitation_endpoint(client: TestClient, auth_override):
    mock_result = {
        "group_id": "grp_1",
        "user_id": "usr_friend",
        "group_name": "Tokyo Foodies",
        "message": "Welcome!",
    }

    with patch(
        "modules.invitation.InvitationService.accept_invitation",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        resp = client.post(
            "/invitations/accept",
            json={"token": "tok_abc"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_id"] == "grp_1"
        assert data["user_id"] == "usr_friend"


def test_cancel_invitation_endpoint(client: TestClient, auth_override):
    with patch(
        "modules.invitation.InvitationService.cancel_invitation",
        new_callable=AsyncMock,
    ):
        resp = client.delete("/invitations/inv_123")
        assert resp.status_code == 204
