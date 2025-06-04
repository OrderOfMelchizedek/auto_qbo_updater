"""Authentication dependencies for FastAPI."""
import logging
from typing import Annotated, Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.services.auth.jwt_handler import JWTError, get_current_user

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


async def get_current_active_user(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> Dict[str, Any]:
    """
    Get the current active user from the JWT token.

    Args:
        token: The JWT token from the Authorization header

    Returns:
        User information dictionary

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user = get_current_user(token)
        return user
    except JWTError as e:
        logger.warning(f"Authentication failed: {e}")
        raise credentials_exception


# Type alias for dependency injection
CurrentUser = Annotated[Dict[str, Any], Depends(get_current_active_user)]
