"""JWT token handling for authentication."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError as JoseJWTError
from jose import jwt

from src.config.settings import settings
from src.utils.exceptions import DonationProcessingError

logger = logging.getLogger(__name__)


class JWTError(DonationProcessingError):
    """Exception raised for JWT-related errors."""

    pass


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: The data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token as string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    logger.debug(f"Created JWT token for: {data.get('sub', 'unknown')}")
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: The JWT token to decode

    Returns:
        Decoded token payload

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JoseJWTError as e:
        if "expired" in str(e).lower():
            logger.warning("Attempted to use expired token")
            raise JWTError("Token has expired", details={"error": str(e)})
        logger.error(f"JWT decode error: {e}")
        raise JWTError("Could not validate token", details={"error": str(e)})


def get_current_user(token: str) -> Dict[str, Any]:
    """
    Get the current user from a JWT token.

    Args:
        token: The JWT token

    Returns:
        User information dictionary

    Raises:
        JWTError: If token is invalid or missing required claims
    """
    payload = decode_access_token(token)

    # Check for required claims
    if "sub" not in payload:
        raise JWTError("Token missing required claims", details={"missing": ["sub"]})

    user_email = payload.get("sub")
    user_role = payload.get("role", "user")

    return {
        "email": user_email,
        "role": user_role,
        "token_issued_at": payload.get("iat"),
        "token_expires_at": payload.get("exp"),
    }
