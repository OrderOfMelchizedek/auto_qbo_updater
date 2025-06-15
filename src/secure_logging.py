"""Secure logging utilities to filter sensitive data."""
import logging
import re
from typing import Any, Dict, Optional


class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive data from logs."""

    # Patterns to detect sensitive data
    SENSITIVE_PATTERNS = [
        # Session IDs (32 char hex strings)
        (r"\b[a-f0-9]{32}\b", "[SESSION_ID_REDACTED]"),
        # OAuth tokens (longer base64-like strings)
        (r"Bearer\s+[A-Za-z0-9\-_=]+", "Bearer [TOKEN_REDACTED]"),
        # Access/refresh tokens in JSON
        (r'"access_token"\s*:\s*"[^"]*"', '"access_token": "[REDACTED]"'),
        (r'"refresh_token"\s*:\s*"[^"]*"', '"refresh_token": "[REDACTED]"'),
        # State parameters (CSRF tokens)
        (r"state=[A-Za-z0-9\-_=]+", "state=[STATE_REDACTED]"),
        # Authorization codes
        (r"code=[A-Za-z0-9\-_=]+", "code=[CODE_REDACTED]"),
        # Customer IDs that look like numbers
        (r'customer_id["\']?\s*:\s*["\']?\d{6,}', "customer_id: [ID_REDACTED]"),
        # Email addresses
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
        # Phone numbers
        (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE_REDACTED]"),
        # SSNs
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log records."""
        # Apply filters to the message
        if hasattr(record, "msg"):
            record.msg = self._redact_sensitive_data(str(record.msg))

        # Apply filters to args if present
        if hasattr(record, "args") and record.args:
            if isinstance(record.args, dict):
                record.args = self._redact_dict(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(
                    self._redact_sensitive_data(str(arg)) for arg in record.args
                )

        return True

    def _redact_sensitive_data(self, text: str) -> str:
        """Redact sensitive data from text."""
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact sensitive data from dictionaries."""
        redacted: Dict[str, Any] = {}
        sensitive_keys = {
            "password",
            "token",
            "secret",
            "key",
            "session_id",
            "access_token",
            "refresh_token",
            "authorization",
            "cookie",
            "csrf",
            "state",
            "code",
        }

        for key, value in data.items():
            # Check if key contains sensitive words
            if any(sensitive_word in key.lower() for sensitive_word in sensitive_keys):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, str):
                redacted[key] = self._redact_sensitive_data(value)
            elif isinstance(value, (list, tuple)):
                redacted[key] = [
                    self._redact_sensitive_data(str(item)) for item in value
                ]
            else:
                redacted[key] = value

        return redacted


class AuditLogger:
    """Logger for security audit events."""

    def __init__(self, name: str = "security_audit"):
        """Initialize audit logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Add secure filter
        self.logger.addFilter(SensitiveDataFilter())

        # Create handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - AUDIT - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_auth_attempt(
        self,
        session_id: str,
        ip_address: str,
        success: bool,
        reason: Optional[str] = None,
    ) -> None:
        """Log authentication attempt."""
        self.logger.info(
            f"AUTH_ATTEMPT - Session: {session_id[:8]}..., IP: {ip_address}, "
            f"Success: {success}, Reason: {reason or 'N/A'}"
        )

    def log_token_refresh(
        self, session_id: str, success: bool, error: Optional[str] = None
    ) -> None:
        """Log token refresh event."""
        self.logger.info(
            f"TOKEN_REFRESH - Session: {session_id[:8]}..., Success: {success}, "
            f"Error: {error or 'None'}"
        )

    def log_token_revoke(self, session_id: str, ip_address: str) -> None:
        """Log token revocation."""
        self.logger.info(
            f"TOKEN_REVOKE - Session: {session_id[:8]}..., IP: {ip_address}"
        )

    def log_api_access(
        self,
        session_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        ip_address: str,
    ) -> None:
        """Log API access."""
        self.logger.info(
            f"API_ACCESS - Session: {session_id[:8]}..., Endpoint: {endpoint}, "
            f"Method: {method}, Status: {status_code}, IP: {ip_address}"
        )

    def log_data_access(
        self, session_id: str, resource_type: str, resource_id: str, action: str
    ) -> None:
        """Log data access events."""
        self.logger.info(
            f"DATA_ACCESS - Session: {session_id[:8]}..., Resource: {resource_type}, "
            f"ID: {resource_id[:8]}..., Action: {action}"
        )

    def log_security_event(
        self,
        event_type: str,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log generic security event."""
        msg = f"SECURITY_EVENT - Type: {event_type}"
        if session_id:
            msg += f", Session: {session_id[:8]}..."
        if details:
            # Redact sensitive data from details
            redacted_details = SensitiveDataFilter()._redact_dict(details)
            msg += f", Details: {redacted_details}"
        self.logger.warning(msg)


def setup_secure_logging(app_logger: logging.Logger) -> None:
    """Set up secure logging for an application logger."""
    # Add sensitive data filter to existing logger
    app_logger.addFilter(SensitiveDataFilter())

    # Adjust log level if needed
    if app_logger.level < logging.INFO:
        app_logger.setLevel(logging.INFO)


# Create global audit logger instance
audit_logger = AuditLogger()
