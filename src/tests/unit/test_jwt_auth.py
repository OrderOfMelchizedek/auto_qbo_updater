"""Unit tests for JWT authentication."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt

from src.services.auth.jwt_handler import (
    JWTError,
    create_access_token,
    decode_access_token,
    get_current_user,
)


def test_create_access_token():
    """Test JWT token creation."""
    data = {"sub": "user@example.com", "role": "admin"}
    token = create_access_token(data)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_with_expiry():
    """Test JWT token creation with custom expiry."""
    data = {"sub": "user@example.com"}
    expires_delta = timedelta(minutes=30)

    token = create_access_token(data, expires_delta)

    # Decode to check expiry
    decoded = jwt.decode(
        token,
        "dummy_key",
        algorithms=["HS256"],
        options={"verify_signature": False, "verify_exp": False},
    )
    assert "exp" in decoded
    assert decoded["sub"] == "user@example.com"


def test_decode_access_token_valid():
    """Test decoding a valid JWT token."""
    data = {"sub": "user@example.com", "role": "admin"}
    token = create_access_token(data)

    decoded = decode_access_token(token)

    assert decoded["sub"] == "user@example.com"
    assert decoded["role"] == "admin"


def test_decode_access_token_expired():
    """Test decoding an expired JWT token."""
    data = {"sub": "user@example.com"}
    # Create token that expires immediately
    expires_delta = timedelta(seconds=-1)

    with patch("src.services.auth.jwt_handler.datetime") as mock_datetime:
        # Mock datetime to create an expired token
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_datetime.now.return_value = past_time
        mock_datetime.timedelta = timedelta

        token = create_access_token(data, expires_delta)

    with pytest.raises(JWTError) as exc_info:
        decode_access_token(token)

    assert "Token has expired" in str(exc_info.value)


def test_decode_access_token_invalid():
    """Test decoding an invalid JWT token."""
    invalid_token = "invalid.token.here"

    with pytest.raises(JWTError) as exc_info:
        decode_access_token(invalid_token)

    assert "Could not validate token" in str(exc_info.value)


def test_get_current_user_valid_token():
    """Test getting current user from valid token."""
    data = {"sub": "user@example.com", "role": "admin"}
    token = create_access_token(data)

    user = get_current_user(token)

    assert user["email"] == "user@example.com"
    assert user["role"] == "admin"


def test_get_current_user_missing_sub():
    """Test getting current user from token without sub claim."""
    # Create token without 'sub' claim
    with patch("src.services.auth.jwt_handler.decode_access_token") as mock_decode:
        mock_decode.return_value = {"role": "admin"}  # Missing 'sub'

        with pytest.raises(JWTError) as exc_info:
            get_current_user("fake_token")

        assert "Token missing required claims" in str(exc_info.value)
