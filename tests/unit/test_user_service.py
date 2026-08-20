from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from passlib.hash import bcrypt

from modules.user import (
    CreateUserRequest,
    LoginRequest,
    UserService,
)
from modules.user.models import UserORM
from shared.errors import AuthenticationError, ConflictError


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def user_service(mock_session):
    return UserService(mock_session)


@pytest.mark.asyncio
async def test_create_user_happy_path(user_service):
    request = CreateUserRequest(email="test@example.com", name="Test", password="password123")
    user_service._repo.exists_by_email = AsyncMock(return_value=False)

    mock_orm = UserORM(
        id="123",
        email="test@example.com",
        name="Test",
        hashed_password="hash",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    user_service._repo.create = AsyncMock(return_value=mock_orm)

    user = await user_service.create_user(request)
    assert user.email == "test@example.com"
    assert user.name == "Test"
    assert not hasattr(user, "password")


@pytest.mark.asyncio
async def test_create_user_duplicate_email(user_service):
    request = CreateUserRequest(email="test@example.com", name="Test", password="password123")
    user_service._repo.exists_by_email = AsyncMock(return_value=True)

    with pytest.raises(ConflictError) as exc:
        await user_service.create_user(request)
    assert "Email already exists" in str(exc.value)


@pytest.mark.asyncio
async def test_authenticate_correct_password(user_service):
    request = LoginRequest(email="test@example.com", password="password123")
    hashed = bcrypt.hash("password123")
    mock_orm = UserORM(
        id="123", email="test@example.com", name="Test", hashed_password=hashed, is_active=True
    )

    user_service._repo.get_by_email = AsyncMock(return_value=mock_orm)

    tokens = await user_service.authenticate(request)
    assert tokens.access_token
    assert tokens.refresh_token


@pytest.mark.asyncio
async def test_authenticate_wrong_password(user_service):
    request = LoginRequest(email="test@example.com", password="wrongpassword")
    hashed = bcrypt.hash("password123")
    mock_orm = UserORM(
        id="123", email="test@example.com", name="Test", hashed_password=hashed, is_active=True
    )

    user_service._repo.get_by_email = AsyncMock(return_value=mock_orm)

    with pytest.raises(AuthenticationError):
        await user_service.authenticate(request)


@pytest.mark.asyncio
async def test_authenticate_user_not_found(user_service):
    request = LoginRequest(email="test@example.com", password="password123")
    user_service._repo.get_by_email = AsyncMock(return_value=None)

    with pytest.raises(AuthenticationError):
        await user_service.authenticate(request)
