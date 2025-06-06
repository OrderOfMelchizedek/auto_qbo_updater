"""QuickBooks OAuth2 authentication module."""
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from cryptography.fernet import Fernet
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from intuitlib.exceptions import AuthClientError

from .config import Config, session_backend

logger = logging.getLogger(__name__)


class QuickBooksAuth:
    """Handle QuickBooks OAuth2 authentication flow."""

    def __init__(self):
        """Initialize QuickBooks OAuth2 client."""
        self.client_id = Config.QBO_CLIENT_ID
        self.client_secret = Config.QBO_CLIENT_SECRET
        self.redirect_uri = Config.QBO_REDIRECT_URI
        self.environment = Config.QBO_ENVIRONMENT

        # Initialize Intuit OAuth client
        self.auth_client = AuthClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            environment=self.environment,
        )

        # Initialize encryption for token storage
        self.cipher_suite = Fernet(Config.get_or_create_encryption_key())

    def get_authorization_url(self, session_id: str) -> Tuple[str, str]:
        """
        Generate authorization URL for QuickBooks OAuth2 flow.

        Args:
            session_id: Unique session identifier

        Returns:
            Tuple of (authorization_url, state)
        """
        # Generate CSRF state token that includes session ID
        # Format: base64(json({csrf: token, sid: session_id}))
        import base64
        import json

        csrf_token = secrets.token_urlsafe(32)
        state_data = {"csrf": csrf_token, "sid": session_id}
        state = (
            base64.urlsafe_b64encode(json.dumps(state_data).encode())
            .decode()
            .rstrip("=")
        )

        # Store state in session for validation
        session_data = {
            "state": state,
            "csrf_token": csrf_token,
            "session_id": session_id,
        }
        session_backend.store_auth_state(session_id, session_data)

        # Define required scopes
        scopes = [Scopes.ACCOUNTING]

        # Get authorization URL
        auth_url = self.auth_client.get_authorization_url(scopes)

        # Check if state already exists in URL
        if "state=" not in auth_url:
            # Append our custom state parameter
            separator = "&" if "?" in auth_url else "?"
            auth_url = f"{auth_url}{separator}state={state}"
        else:
            # Replace the existing state with our custom state
            import re

            auth_url = re.sub(r"state=[^&]*", f"state={state}", auth_url)

        logger.info(f"Generated authorization URL for session {session_id}")
        return auth_url, state

    def exchange_authorization_code(
        self, code: str, realm_id: str, state: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access tokens.

        Args:
            code: Authorization code from QuickBooks
            realm_id: QuickBooks company ID
            state: CSRF state token
            session_id: Session identifier (optional, can be extracted from state)

        Returns:
            Dict containing token information

        Raises:
            ValueError: If state validation fails
            AuthClientError: If token exchange fails
        """
        # If no session_id provided, try to extract from state
        csrf_token = None
        if not session_id:
            try:
                import base64
                import json

                # Add padding if needed
                padded_state = state + "=" * (4 - len(state) % 4)
                state_data = json.loads(base64.urlsafe_b64decode(padded_state))
                session_id = state_data.get("sid")
                csrf_token = state_data.get("csrf")
            except Exception:
                raise ValueError("Invalid state parameter format")

        if not session_id:
            raise ValueError("No session ID found in state parameter")

        # Validate state
        session_data = session_backend.get_auth_state(session_id)
        if not session_data:
            raise ValueError("Invalid session - state not found")

        # Check if state matches (for backward compatibility)
        if session_data.get("state") != state and (
            not csrf_token or session_data.get("csrf_token") != csrf_token
        ):
            raise ValueError("Invalid state parameter - possible CSRF attack")

        try:
            # Exchange code for tokens
            self.auth_client.get_bearer_token(code, realm_id=realm_id)

            # Extract token data
            token_data = {
                "access_token": self.auth_client.access_token,
                "refresh_token": self.auth_client.refresh_token,
                "expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=3600),  # 1 hour
                "refresh_expires_at": datetime.now(timezone.utc)
                + timedelta(days=100),  # 100 days
                "realm_id": realm_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Store encrypted tokens
            self._store_tokens(session_id, token_data)

            logger.info(
                f"Successfully exchanged auth code for tokens (session: {session_id})"
            )
            return {
                "success": True,
                "realm_id": realm_id,
                "expires_at": token_data["expires_at"].isoformat(),
            }

        except AuthClientError as e:
            logger.error(f"Failed to exchange auth code: {e}")
            raise

        finally:
            # Clean up state
            session_backend.delete_auth_state(session_id)

    def refresh_access_token(self, session_id: str) -> Dict[str, Any]:
        """
        Refresh expired access token.

        Args:
            session_id: Session identifier

        Returns:
            Dict with new token information

        Raises:
            ValueError: If no valid refresh token found
            AuthClientError: If refresh fails
        """
        token_data = self._get_tokens(session_id)
        if not token_data:
            raise ValueError("No tokens found for session")
        if not token_data.get("refresh_token"):
            raise ValueError("No valid refresh token found")

        # Check if refresh token is expired
        refresh_expires_at = datetime.fromisoformat(token_data["refresh_expires_at"])
        if refresh_expires_at <= datetime.now(timezone.utc):
            raise ValueError("Refresh token has expired - reauthorization required")

        try:
            # Refresh the token
            self.auth_client.refresh(refresh_token=token_data["refresh_token"])

            # Update token data
            token_data.update(
                {
                    "access_token": self.auth_client.access_token,
                    "refresh_token": self.auth_client.refresh_token,
                    "expires_at": datetime.now(timezone.utc) + timedelta(seconds=3600),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            # Store updated tokens
            self._store_tokens(session_id, token_data)

            logger.info(f"Successfully refreshed access token (session: {session_id})")
            return {
                "success": True,
                "expires_at": token_data["expires_at"].isoformat(),
            }

        except AuthClientError as e:
            logger.error(f"Failed to refresh token: {e}")
            raise

    def revoke_tokens(self, session_id: str) -> bool:
        """
        Revoke all tokens for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if revocation successful
        """
        token_data = self._get_tokens(session_id)
        if not token_data:
            return True  # No tokens to revoke

        try:
            # Revoke the refresh token (this also revokes access token)
            if token_data.get("refresh_token"):
                self.auth_client.revoke(token=token_data["refresh_token"])

            # Delete stored tokens
            session_backend.delete_tokens(session_id)

            logger.info(f"Successfully revoked tokens (session: {session_id})")
            return True

        except AuthClientError as e:
            logger.error(f"Failed to revoke tokens: {e}")
            # Delete tokens locally even if revocation failed
            session_backend.delete_tokens(session_id)
            return False

    def get_valid_access_token(self, session_id: str) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.

        Args:
            session_id: Session identifier

        Returns:
            Valid access token or None if not authenticated
        """
        token_data = self._get_tokens(session_id)
        if not token_data:
            return None

        # Check if access token is expired
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        if expires_at <= datetime.now(timezone.utc) + timedelta(minutes=5):
            # Refresh if expired or expiring soon
            try:
                self.refresh_access_token(session_id)
                token_data = self._get_tokens(session_id)
                if not token_data:
                    return None
            except (ValueError, AuthClientError):
                return None

        return token_data.get("access_token")

    def get_auth_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get current authentication status.

        Args:
            session_id: Session identifier

        Returns:
            Dict with authentication status
        """
        token_data = self._get_tokens(session_id)
        if not token_data:
            return {"authenticated": False}

        if not isinstance(token_data, dict):
            return {"authenticated": False}

        expires_at = datetime.fromisoformat(token_data["expires_at"])
        refresh_expires_at = datetime.fromisoformat(token_data["refresh_expires_at"])
        now = datetime.now(timezone.utc)

        return {
            "authenticated": True,
            "realm_id": token_data.get("realm_id"),
            "access_token_valid": expires_at > now,
            "access_token_expires_at": expires_at.isoformat(),
            "refresh_token_valid": refresh_expires_at > now,
            "refresh_token_expires_at": refresh_expires_at.isoformat(),
        }

    def _store_tokens(self, session_id: str, token_data: Dict[str, Any]) -> None:
        """Store encrypted tokens in session backend."""
        # Convert datetime objects to strings for JSON serialization
        serializable_data = token_data.copy()
        for key in ["expires_at", "refresh_expires_at"]:
            if key in serializable_data and hasattr(
                serializable_data[key], "isoformat"
            ):
                serializable_data[key] = serializable_data[key].isoformat()

        # Encrypt sensitive data
        encrypted_data = self.cipher_suite.encrypt(
            json.dumps(serializable_data).encode()
        )

        # Store in session backend
        session_backend.store_tokens(session_id, encrypted_data)

    def _get_tokens(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt tokens from session backend."""
        encrypted_data = session_backend.get_tokens(session_id)
        if not encrypted_data:
            return None

        try:
            # Decrypt data
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt token data: {e}")
            return None


# Global instance
try:
    qbo_auth: Optional[QuickBooksAuth] = QuickBooksAuth()
except Exception as e:
    logger.error(f"Failed to initialize QuickBooks auth: {e}")
    qbo_auth = None
