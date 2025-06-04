"""Authentication endpoints."""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from src.api.dependencies.auth import CurrentUser
from src.config.settings import settings
from src.services.auth.jwt_handler import create_access_token
from src.services.auth.quickbooks_oauth import QuickBooksOAuth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Initialize QuickBooks OAuth handler
qb_oauth = QuickBooksOAuth(
    client_id=settings.QBO_CLIENT_ID,
    client_secret=settings.QBO_CLIENT_SECRET,
    redirect_uri=settings.QBO_REDIRECT_URI,
    environment=settings.QBO_ENVIRONMENT,
)


@router.get("/quickbooks")
async def initiate_quickbooks_auth() -> Dict[str, str]:
    """
    Initiate QuickBooks OAuth flow.

    Returns:
        Dictionary with auth_url to redirect user to
    """
    auth_url = qb_oauth.generate_auth_url()
    logger.info("Initiated QuickBooks OAuth flow")
    return {"auth_url": auth_url}


@router.get("/callback")
async def quickbooks_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Handle QuickBooks OAuth callback.

    Args:
        code: Authorization code from QuickBooks
        state: State parameter for CSRF protection
        error: Error code if authorization failed
        error_description: Error description if authorization failed

    Returns:
        Success message and JWT token for the app

    Raises:
        HTTPException: If authorization failed
    """
    if error:
        logger.error(f"QuickBooks OAuth error: {error} - {error_description}")
        raise HTTPException(
            status_code=400,
            detail=f"QuickBooks authorization failed: {error}",
        )

    if not code:
        raise HTTPException(
            status_code=400,
            detail="No authorization code provided",
        )

    try:
        # Exchange code for tokens
        tokens = qb_oauth.handle_oauth_callback(code, state or "")

        # Create JWT token for our app
        jwt_data = {
            "sub": tokens.get("company_id"),  # Using company ID as subject
            "role": "quickbooks_connected",
            "qb_access_token": tokens.get("access_token"),
            "qb_refresh_token": tokens.get("refresh_token"),
        }

        app_token = create_access_token(jwt_data)

        logger.info(
            f"Successfully connected QuickBooks company: {tokens.get('company_id')}"
        )

        return {
            "message": "Successfully connected to QuickBooks",
            "access_token": app_token,
            "token_type": "bearer",
            "company_id": tokens.get("company_id"),
        }

    except Exception as e:
        logger.error(f"Failed to handle OAuth callback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to complete QuickBooks authorization",
        )


@router.get("/me")
async def get_current_user_info(current_user: CurrentUser) -> Dict[str, Any]:
    """
    Get current user information.

    Args:
        current_user: The authenticated user

    Returns:
        User information
    """
    return current_user
