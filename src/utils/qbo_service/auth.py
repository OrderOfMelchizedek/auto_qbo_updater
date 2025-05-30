"""
QuickBooks Online Authentication Service.

This module handles OAuth2 authentication flow, token management,
and token persistence using Redis.
"""

import base64
import logging
import time
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlencode

import redis
import requests

from ..exceptions import QBOAPIException
from ..retry import retry_on_failure

logger = logging.getLogger(__name__)


class QBOAuthService:
    """Service for handling QuickBooks Online OAuth2 authentication."""

    # Default timeout for API requests (30 seconds)
    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        environment: str = "sandbox",
        redis_client: Optional[redis.Redis] = None,
    ):
        """Initialize the QBO auth service with OAuth credentials.

        Args:
            client_id: QBO Client ID
            client_secret: QBO Client Secret
            redirect_uri: OAuth redirect URI
            environment: 'sandbox' or 'production'
            redis_client: Optional Redis client for token persistence
        """
        if environment not in ["sandbox", "production"]:
            raise ValueError(f"Environment must be 'sandbox' or 'production', got: {environment}")

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.environment = environment
        self.redis_client = redis_client

        # Base URLs for QBO API
        if environment == "sandbox":
            self.auth_endpoint = "https://appcenter.intuit.com/connect/oauth2"
            self.token_endpoint = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
            self.api_base = "https://sandbox-quickbooks.api.intuit.com/v3/company/"
        else:
            self.auth_endpoint = "https://appcenter.intuit.com/connect/oauth2"
            self.token_endpoint = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
            self.api_base = "https://quickbooks.api.intuit.com/v3/company/"

        # OAuth tokens (to be set during authorization flow)
        self._access_token = None
        self._refresh_token = None
        self._realm_id = None
        self._token_expires_at = 0

        # Token persistence key prefix
        self.token_key_prefix = f"qbo_tokens:{environment}:"

        # Load tokens from Redis if available
        if self.redis_client:
            self._load_tokens_from_redis()

    # Token properties with Redis persistence
    @property
    def access_token(self):
        """Get the current access token."""
        return self._access_token

    @access_token.setter
    def access_token(self, value):
        self._access_token = value
        self._save_token_to_redis("access_token", value)

    @property
    def refresh_token(self):
        """Get the current refresh token."""
        return self._refresh_token

    @refresh_token.setter
    def refresh_token(self, value):
        self._refresh_token = value
        self._save_token_to_redis("refresh_token", value)

    @property
    def realm_id(self):
        """Get the QBO company realm ID."""
        return self._realm_id

    @realm_id.setter
    def realm_id(self, value):
        self._realm_id = value
        self._save_token_to_redis("realm_id", value)

    @property
    def token_expires_at(self):
        """Get the token expiration timestamp."""
        return self._token_expires_at

    @token_expires_at.setter
    def token_expires_at(self, value):
        self._token_expires_at = value
        self._save_token_to_redis("token_expires_at", str(value))

    def _save_token_to_redis(self, key: str, value: Optional[str]):
        """Save a token value to Redis if client is available."""
        if self.redis_client and value is not None:
            try:
                redis_key = f"{self.token_key_prefix}{key}"
                # Set with 90 day expiration (QBO refresh tokens last 100 days)
                self.redis_client.setex(redis_key, 90 * 24 * 60 * 60, value)
                logger.debug(f"Saved {key} to Redis")
            except Exception as e:
                logger.error(f"Failed to save {key} to Redis: {e}")

    def _load_tokens_from_redis(self):
        """Load tokens from Redis if available."""
        if not self.redis_client:
            return

        try:
            # Load each token field
            access_token = self.redis_client.get(f"{self.token_key_prefix}access_token")
            if access_token:
                self._access_token = access_token.decode("utf-8")

            refresh_token = self.redis_client.get(f"{self.token_key_prefix}refresh_token")
            if refresh_token:
                self._refresh_token = refresh_token.decode("utf-8")

            realm_id = self.redis_client.get(f"{self.token_key_prefix}realm_id")
            if realm_id:
                self._realm_id = realm_id.decode("utf-8")

            token_expires_at = self.redis_client.get(f"{self.token_key_prefix}token_expires_at")
            if token_expires_at:
                try:
                    self._token_expires_at = int(token_expires_at.decode("utf-8"))
                except ValueError:
                    self._token_expires_at = 0

            if self._access_token:
                logger.info(f"Loaded QBO tokens from Redis (realm_id: {self._realm_id})")
        except Exception as e:
            logger.error(f"Failed to load tokens from Redis: {e}")

    def clear_tokens(self):
        """Clear all tokens from memory and Redis."""
        self._access_token = None
        self._refresh_token = None
        self._realm_id = None
        self._token_expires_at = 0

        if self.redis_client:
            try:
                # Clear all token keys from Redis
                for key in ["access_token", "refresh_token", "realm_id", "token_expires_at"]:
                    redis_key = f"{self.token_key_prefix}{key}"
                    self.redis_client.delete(redis_key)
                logger.info("Cleared QBO tokens from Redis")
            except Exception as e:
                logger.error(f"Failed to clear tokens from Redis: {e}")

    def get_authorization_url(self) -> str:
        """Get the QBO authorization URL for OAuth flow.

        Returns:
            Authorization URL to redirect the user to
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "com.intuit.quickbooks.accounting",
            "redirect_uri": self.redirect_uri,
            "state": str(int(time.time())),  # Simple anti-forgery state token
        }

        auth_url = f"{self.auth_endpoint}?{urlencode(params)}"
        return auth_url

    @retry_on_failure(max_attempts=3, exceptions=(requests.RequestException, QBOAPIException))
    def get_tokens(self, authorization_code: str, realm_id: str) -> bool:
        """Exchange authorization code for access and refresh tokens.

        Args:
            authorization_code: OAuth authorization code from callback
            realm_id: QBO company ID

        Returns:
            True if successful, False otherwise
        """
        try:
            auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            data = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self.redirect_uri,
            }

            response = requests.post(self.token_endpoint, headers=headers, data=data, timeout=30)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                self.realm_id = realm_id
                self.token_expires_at = int(time.time()) + token_data.get("expires_in", 3600)
                logger.info("Successfully obtained QBO access tokens")
                return True
            else:
                logger.error(f"Failed to get QBO tokens: {response.status_code} - {response.text}")
                return False

        except requests.RequestException as e:
            logger.error(f"Network error getting QBO tokens: {str(e)}")
            raise QBOAPIException(
                f"Network error while getting tokens: {str(e)}",
                status_code=None,
                response_text=None,
                user_message="Unable to connect to QuickBooks. Please check your internet connection.",
            )
        except QBOAPIException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_tokens: {str(e)}")
            raise QBOAPIException(
                f"Unexpected error: {str(e)}",
                user_message="An unexpected error occurred. Please try again.",
            )

    def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token.

        Returns:
            True if successful, False otherwise
        """
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False

        try:
            auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            data = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}

            response = requests.post(self.token_endpoint, headers=headers, data=data, timeout=self.DEFAULT_TIMEOUT)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token", self.refresh_token)
                self.token_expires_at = int(time.time()) + token_data.get("expires_in", 3600)
                logger.info("Successfully refreshed QBO access token")
                return True
            else:
                logger.error(f"Error refreshing token: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Exception in refresh_access_token: {str(e)}")
            return False

    def refresh_tokens(self) -> bool:
        """Alias for refresh_access_token for compatibility.

        Returns:
            True if successful, False otherwise
        """
        return self.refresh_access_token()

    def is_token_valid(self) -> bool:
        """Check if the current access token is valid.

        Returns:
            True if token exists and not expired, False otherwise
        """
        if not self.access_token or not self.token_expires_at:
            return False

        # Check if token is expired (with 60 second buffer)
        return int(time.time()) < (self.token_expires_at - 60)

    def get_token_info(self) -> Optional[Dict[str, any]]:
        """Get information about current token status.

        Returns:
            Dictionary with token status information or None if no token
        """
        if not self.access_token:
            return None

        try:
            expires_at_iso = (
                datetime.fromtimestamp(self.token_expires_at).isoformat() if self.token_expires_at else None
            )
            expires_in_hours = max(0, (self.token_expires_at - int(time.time())) / 3600) if self.token_expires_at else 0

            return {
                "realm_id": self.realm_id,
                "expires_at": expires_at_iso,
                "expires_in_hours": expires_in_hours,
                "is_valid": self.is_token_valid(),
            }
        except Exception:
            return None

    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication for QBO API calls.

        Returns:
            Dictionary of HTTP headers

        Raises:
            QBOAPIException: If no valid access token is available
        """
        # Check if token is expired (or will expire soon)
        if self.token_expires_at:
            try:
                # Handle both integer timestamp and string formats
                if isinstance(self.token_expires_at, str):
                    expires_at = int(datetime.fromisoformat(self.token_expires_at.replace("Z", "+00:00")).timestamp())
                else:
                    expires_at = self.token_expires_at

                # If token is expired or will expire in next 5 minutes, refresh it
                if int(time.time()) >= (expires_at - 300):
                    logger.info("Access token expired or expiring soon, attempting refresh")
                    if not self.refresh_access_token():
                        raise QBOAPIException(
                            "Failed to refresh expired access token",
                            user_message="QuickBooks authentication expired. Please reconnect to QuickBooks.",
                        )
            except Exception as e:
                if isinstance(e, QBOAPIException):
                    raise
                logger.error(f"Error checking token expiry: {e}")

        if not self.access_token:
            raise QBOAPIException(
                "No access token available",
                user_message="Please connect to QuickBooks first.",
            )

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
