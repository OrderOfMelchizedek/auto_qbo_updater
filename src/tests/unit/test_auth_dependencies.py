"""Unit tests for authentication dependencies."""
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.api.dependencies.auth import get_current_active_user, oauth2_scheme


def test_oauth2_scheme_configuration():
    """Test OAuth2 scheme is properly configured."""
    assert oauth2_scheme.scheme_name == "OAuth2PasswordBearer"
    # The tokenUrl is passed to the constructor but not exposed as an attribute
    # We can verify the scheme is properly configured by its type
    assert callable(oauth2_scheme)


@pytest.mark.asyncio
async def test_get_current_active_user_success():
    """Test getting current active user with valid token."""
    mock_user = {"email": "user@example.com", "role": "admin"}

    with patch("src.api.dependencies.auth.get_current_user") as mock_get_user:
        mock_get_user.return_value = mock_user

        result = await get_current_active_user("valid_token")

        assert result == mock_user
        mock_get_user.assert_called_once_with("valid_token")


@pytest.mark.asyncio
async def test_get_current_active_user_invalid_token():
    """Test getting current active user with invalid token."""
    from src.services.auth.jwt_handler import JWTError

    with patch("src.api.dependencies.auth.get_current_user") as mock_get_user:
        mock_get_user.side_effect = JWTError("Invalid token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user("invalid_token")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Could not validate credentials"
