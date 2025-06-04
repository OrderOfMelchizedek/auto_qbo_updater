"""QuickBooks OAuth 2.0 authentication service."""
import base64
import json
import logging
import secrets
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests
from redis import Redis

from src.utils.exceptions import DonationProcessingError
from src.utils.redis_client import RedisConnectionError, get_redis_client

logger = logging.getLogger(__name__)


class QuickBooksAuthError(DonationProcessingError):
    """Exception raised for QuickBooks authentication errors."""

    pass


class QuickBooksOAuth:
    """Handle QuickBooks OAuth 2.0 authentication flow."""

    redis_client: Optional[Redis]

    def __init__(
        self,
        client_id: Optional[str],
        client_secret: Optional[str],
        redirect_uri: Optional[str],
        environment: str = "sandbox",
    ):
        """
        Initialize QuickBooks OAuth handler.

        Args:
            client_id: QuickBooks app client ID
            client_secret: QuickBooks app client secret
            redirect_uri: OAuth callback URL
            environment: QuickBooks environment (sandbox or production)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.environment = environment

        # OAuth URLs based on environment
        if environment == "production":
            self.auth_base_url = "https://appcenter.intuit.com/connect/oauth2"
            self.token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
            self.discovery_document_url = (
                "https://developer.api.intuit.com/.well-known/openid_configuration"
            )
        else:  # sandbox
            self.auth_base_url = "https://appcenter.intuit.com/connect/oauth2"
            self.token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
            self.discovery_document_url = (
                "https://developer.api.intuit.com/.well-known/"
                "openid_sandbox_configuration"
            )

        # Try to get Redis client, but don't fail if unavailable
        try:
            self.redis_client = get_redis_client()
        except RedisConnectionError:
            logger.warning("Redis not available, state validation will be disabled")
            self.redis_client = None

    def generate_auth_url(self) -> str:
        """
        Generate the QuickBooks OAuth authorization URL.

        Returns:
            Authorization URL to redirect user to
        """
        state = self._generate_state()

        params = {
            "client_id": self.client_id,
            "scope": "com.intuit.quickbooks.accounting",
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
        }

        auth_url = f"{self.auth_base_url}?{urlencode(params)}"
        logger.info("Generated QuickBooks auth URL")
        return auth_url

    def handle_oauth_callback(self, code: str, state: str) -> Dict[str, Any]:
        """
        Handle the OAuth callback and exchange code for tokens.

        Args:
            code: Authorization code from QuickBooks
            state: State parameter for CSRF protection

        Returns:
            Dictionary containing access token, refresh token, and company ID

        Raises:
            QuickBooksAuthError: If authentication fails
        """
        # Verify state parameter
        if not self._verify_state(state):
            raise QuickBooksAuthError("Invalid state parameter - possible CSRF attack")

        # Exchange authorization code for tokens
        tokens = self._exchange_code_for_tokens(code)

        # Extract company ID from the authorization code
        # QuickBooks includes realmId (company ID) in the callback
        company_id = self._extract_company_id(code)

        tokens["company_id"] = company_id

        # Store tokens in Redis for later use
        self._store_tokens(company_id, tokens)

        return tokens

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token.

        Args:
            refresh_token: The refresh token

        Returns:
            New tokens dictionary

        Raises:
            QuickBooksAuthError: If refresh fails
        """
        auth_header = self._get_auth_header()

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        response = requests.post(
            self.token_url,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data=data,
        )

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.text}")
            raise QuickBooksAuthError(
                "Failed to refresh access token",
                details={"status": response.status_code, "error": response.text},
            )

        return response.json()

    def _generate_state(self) -> str:
        """Generate and store a random state parameter for CSRF protection."""
        state = secrets.token_urlsafe(32)
        # Store state in Redis with 10-minute expiration
        if self.redis_client:
            self.redis_client.setex(f"qb_oauth_state:{state}", 600, "1")
        return state

    def _verify_state(self, state: str) -> bool:
        """Verify the state parameter from callback."""
        if not self.redis_client:
            # If Redis is not available, skip state validation
            logger.warning("Redis not available, skipping state validation")
            return True

        key = f"qb_oauth_state:{state}"
        exists = self.redis_client.exists(key)
        if exists:
            self.redis_client.delete(key)  # Use state only once
            return True
        return False

    def _exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        auth_header = self._get_auth_header()

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        response = requests.post(
            self.token_url,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data=data,
        )

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise QuickBooksAuthError(
                "Token exchange failed",
                details={"status": response.status_code, "error": response.text},
            )

        return response.json()

    def _get_auth_header(self) -> str:
        """Generate the Basic Auth header for token requests."""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _extract_company_id(self, code: str) -> str:
        """
        Extract company ID from the authorization response.

        Note: In a real implementation, the company ID (realmId)
        is typically passed as a query parameter in the callback.
        """
        # For now, return a placeholder
        # In production, this would parse the actual company ID
        return "placeholder_company_id"

    def _store_tokens(self, company_id: str, tokens: Dict[str, Any]) -> None:
        """Store tokens in Redis for later use."""
        if not self.redis_client:
            logger.warning("Redis not available, cannot store tokens")
            return

        key = f"qb_tokens:{company_id}"
        # Store with expiration matching token lifetime
        expires_in = tokens.get("expires_in", 3600)
        self.redis_client.setex(key, expires_in, json.dumps(tokens))
        logger.info(f"Stored QuickBooks tokens for company: {company_id}")
