"""
Base class for QuickBooks Online service modules.

Provides common functionality for making API requests.
"""

import logging
from typing import Any, Dict
from urllib.parse import quote

import requests

from ..exceptions import QBOAPIException, RetryableException
from ..retry import retry_on_failure
from .auth import QBOAuthService

logger = logging.getLogger(__name__)


class QBOBaseService:
    """Base class for QBO service modules."""

    # Default timeout for API requests (30 seconds)
    DEFAULT_TIMEOUT = 30

    def __init__(self, auth_service: QBOAuthService):
        """Initialize with an auth service instance.

        Args:
            auth_service: QBOAuthService instance for authentication
        """
        self.auth_service = auth_service

    @property
    def api_base(self) -> str:
        """Get the API base URL."""
        return self.auth_service.api_base

    @property
    def realm_id(self) -> str:
        """Get the realm ID."""
        return self.auth_service.realm_id

    def _escape_query_value(self, value: str) -> str:
        """Escape special characters in query values for QBO API.

        Args:
            value: Query value to escape

        Returns:
            Escaped query value
        """
        # QBO API requires escaping single quotes with backslash
        if not value:
            return value

        # Escape single quotes
        escaped = value.replace("'", "\\'")

        # URL encode other special characters
        return quote(escaped, safe="")

    @retry_on_failure(max_attempts=3, exceptions=(requests.RequestException, RetryableException))
    def _make_qbo_request(
        self,
        method: str,
        endpoint: str,
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None,
        timeout: int = None,
    ) -> Dict[str, Any]:
        """Make a request to the QBO API with error handling and retries.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            Response JSON data

        Raises:
            QBOAPIException: If the request fails
            RetryableException: If the error is retryable
        """
        if not self.realm_id:
            raise QBOAPIException(
                "No realm ID set",
                user_message="QuickBooks company not selected. Please reconnect to QuickBooks.",
            )

        url = f"{self.api_base}{self.realm_id}/{endpoint}"

        try:
            # Get auth headers (may refresh token if needed)
            headers = self.auth_service.get_auth_headers()

            # Make the request
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=timeout or self.DEFAULT_TIMEOUT,
            )

            # Check for successful response
            if response.status_code == 200:
                return response.json()

            # Handle specific error codes
            if response.status_code == 401:
                # Unauthorized - try to refresh token
                logger.info("Got 401 response, attempting to refresh token")
                if self.auth_service.refresh_access_token():
                    # Retry the request with new token
                    raise RetryableException("Token refreshed, retrying request")
                else:
                    raise QBOAPIException(
                        "Authentication failed",
                        status_code=401,
                        response_text=response.text,
                        user_message="QuickBooks authentication failed. Please reconnect to QuickBooks.",
                    )

            elif response.status_code == 429:
                # Rate limited - this is retryable
                raise RetryableException(f"Rate limited: {response.text}")

            elif response.status_code == 403:
                # Forbidden - check if it's a subscription issue
                error_msg = response.text.lower()
                if "subscription" in error_msg or "expired" in error_msg:
                    raise QBOAPIException(
                        f"QuickBooks subscription issue: {response.text}",
                        status_code=403,
                        response_text=response.text,
                        user_message="Your QuickBooks subscription may have expired or lacks required features. Please check your QuickBooks account.",
                    )
                else:
                    raise QBOAPIException(
                        f"Access forbidden: {response.text}",
                        status_code=403,
                        response_text=response.text,
                        user_message="You don't have permission to perform this action in QuickBooks.",
                    )

            elif response.status_code == 404:
                raise QBOAPIException(
                    f"Resource not found: {response.text}",
                    status_code=404,
                    response_text=response.text,
                    user_message="The requested QuickBooks resource was not found.",
                )

            elif response.status_code == 400:
                # Bad request - parse the error message
                try:
                    error_data = response.json()
                    error_msg = self._extract_error_message(error_data)
                    raise QBOAPIException(
                        f"Bad request: {error_msg}",
                        status_code=400,
                        response_text=response.text,
                        user_message=f"QuickBooks rejected the request: {error_msg}",
                    )
                except ValueError:
                    raise QBOAPIException(
                        f"Bad request: {response.text}",
                        status_code=400,
                        response_text=response.text,
                        user_message="QuickBooks rejected the request. Please check your data.",
                    )

            else:
                # Other errors
                raise QBOAPIException(
                    f"QBO API error: {response.status_code} - {response.text}",
                    status_code=response.status_code,
                    response_text=response.text,
                    user_message=f"QuickBooks error (code {response.status_code}). Please try again.",
                )

        except requests.RequestException as e:
            logger.error(f"Network error in QBO request: {str(e)}")
            raise RetryableException(f"Network error: {str(e)}")
        except (QBOAPIException, RetryableException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in QBO request: {str(e)}")
            raise QBOAPIException(
                f"Unexpected error: {str(e)}",
                user_message="An unexpected error occurred. Please try again.",
            )

    def _extract_error_message(self, error_data: Dict[str, Any]) -> str:
        """Extract a readable error message from QBO error response.

        Args:
            error_data: Error response data from QBO

        Returns:
            Human-readable error message
        """
        if isinstance(error_data, dict):
            # Look for Fault.Error structure
            fault = error_data.get("Fault", {})
            errors = fault.get("Error", [])
            if isinstance(errors, list) and errors:
                error = errors[0]
                detail = error.get("Detail", error.get("Message", "Unknown error"))
                return detail
            elif isinstance(errors, dict):
                detail = errors.get("Detail", errors.get("Message", "Unknown error"))
                return detail

        return str(error_data)
