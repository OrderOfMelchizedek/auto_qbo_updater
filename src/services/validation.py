"""
Validation utilities for donation data processing.

This module contains functions for validating and normalizing donation data,
including date validation, amount normalization, and data sanitization.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import dateutil.parser
import pandas as pd

# Constants for date validation
FUTURE_DATE_LIMIT_DAYS = int(
    os.environ.get("FUTURE_DATE_LIMIT_DAYS", "30")
)  # Allow dates up to N days in the future
DATE_WARNING_DAYS = int(
    os.environ.get("DATE_WARNING_DAYS", "730")
)  # Warn for dates older than N days


def sanitize_for_logging(data: Union[Dict, str, List, Any]) -> Union[Dict, str, List, Any]:
    """
    Recursively sanitize sensitive data from dictionaries before logging.

    Args:
        data: Data to sanitize (dict, string, list, or any other type)

    Returns:
        Sanitized version of the data with sensitive values redacted
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            # Check if value is a dict first to allow recursion
            if isinstance(value, dict):
                sanitized[key] = sanitize_for_logging(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    sanitize_for_logging(item) if isinstance(item, dict) else item for item in value
                ]
            # Sensitive field patterns - only redact if not a dict/list
            elif any(
                pattern in key_lower
                for pattern in [
                    "password",
                    "secret",
                    "token",
                    "key",
                    "auth",
                    "credential",
                    "ssn",
                    "social",
                    "tax",
                    "account_number",
                    "routing",
                    "bank",
                ]
            ):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(data, str):
        # Basic pattern matching for sensitive data in strings
        # Redact potential tokens/keys (long alphanumeric strings)
        data = re.sub(r"\b[A-Za-z0-9]{32,}\b", "[REDACTED_TOKEN]", data)
        # Redact potential SSNs
        data = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", data)
        return data
    else:
        return data


def validate_donation_date(
    date_str: str, field_name: str = "date"
) -> Tuple[bool, Optional[str], Optional[pd.Timestamp]]:
    """
    Validate a donation date is within reasonable bounds.

    Args:
        date_str: Date string to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, warning_message, parsed_date)
        - is_valid: True if date is acceptable, False if should be rejected
        - warning_message: Warning message if date is suspicious but acceptable
        - parsed_date: The parsed date object or None if invalid
    """
    if not date_str:
        return True, None, None

    try:
        # Parse the date
        parsed_date = pd.to_datetime(date_str)
        today = pd.Timestamp.now()

        # Check if date is in the future
        if parsed_date > today:
            # Calculate days difference
            # Since parsed_date is at midnight and today has time, we need to handle this carefully
            days_future = (parsed_date.date() - today.date()).days

            if days_future > FUTURE_DATE_LIMIT_DAYS:
                return (
                    False,
                    f"{field_name} is {days_future} days in the future (max allowed: {FUTURE_DATE_LIMIT_DAYS} days)",
                    None,
                )
            elif days_future > 0:
                return True, f"{field_name} is {days_future} days in the future", parsed_date

        # Check if date is too old
        days_old = (today - parsed_date).days
        if days_old > DATE_WARNING_DAYS:
            years_old = days_old // 365
            return True, f"{field_name} is {years_old:.1f} years old - please verify", parsed_date

        # Date is within normal range
        return True, None, parsed_date

    except Exception as e:
        return False, f"Invalid {field_name} format: {str(e)}", None


def validate_environment():
    """
    Validate that all required environment variables are set.

    Raises:
        ValueError: If required environment variables are missing or invalid
    """
    required_vars = {
        "FLASK_SECRET_KEY": "Flask secret key for session management",
        "GEMINI_API_KEY": "Google Gemini API key for AI processing",
        "QBO_CLIENT_ID": "QuickBooks OAuth Client ID",
        "QBO_CLIENT_SECRET": "QuickBooks OAuth Client Secret",
        "QBO_REDIRECT_URI": "QuickBooks OAuth redirect URI",
    }

    missing_vars = []
    for var_name, description in required_vars.items():
        if not os.environ.get(var_name):
            missing_vars.append(f"  - {var_name}: {description}")

    if missing_vars:
        error_msg = "Missing required environment variables:\n" + "\n".join(missing_vars)
        error_msg += "\n\nPlease set these in your .env file. See .env.example for reference."
        raise ValueError(error_msg)

    # Validate optional but recommended variables
    optional_vars = {"QBO_ENVIRONMENT": ("sandbox", "QuickBooks environment (sandbox/production)")}

    for var_name, (default, description) in optional_vars.items():
        if not os.environ.get(var_name):
            print(f"Warning: {var_name} not set. Using default: {default}")
            print(f"         {description}")

    # Validate QBO_ENVIRONMENT value if set
    qbo_env = os.environ.get("QBO_ENVIRONMENT")
    if qbo_env and qbo_env not in ["sandbox", "production"]:
        raise ValueError(
            f"Invalid QBO_ENVIRONMENT: '{qbo_env}'. Must be 'sandbox' or 'production'."
        )

    # Validate URL format for redirect URI
    redirect_uri = os.environ.get("QBO_REDIRECT_URI")
    if redirect_uri and not (
        redirect_uri.startswith("http://") or redirect_uri.startswith("https://")
    ):
        raise ValueError(
            f"Invalid QBO_REDIRECT_URI: '{redirect_uri}'. Must start with http:// or https://"
        )


def normalize_check_number(check_no: Optional[str]) -> Optional[str]:
    """
    Normalize check number for comparison.

    Args:
        check_no: Check number to normalize

    Returns:
        Normalized check number string or None if invalid
    """
    if not check_no:
        return None
    # Extract digits only
    import re

    check_str = re.sub(r"[^0-9]", "", str(check_no))
    if not check_str:
        return None
    # Remove leading zeros
    normalized = check_str.lstrip("0")
    # If all zeros were removed, ensure at least '0' remains
    return normalized if normalized else "0"


def normalize_amount(amount: Optional[Union[str, float, int]]) -> Optional[str]:
    """
    Normalize amount for comparison.

    Args:
        amount: Amount to normalize

    Returns:
        Normalized amount string formatted to 2 decimal places, or None if invalid
    """
    if not amount and amount != 0:
        return None
    # Remove currency symbols, commas, and spaces
    amount_str = str(amount).replace("$", "").replace(",", "").strip()
    if not amount_str:
        return None
    try:
        # Convert to float and format to 2 decimal places
        return f"{float(amount_str):.2f}"
    except (ValueError, TypeError):
        return None


def normalize_donor_name(name: Optional[str]) -> Optional[str]:
    """
    Normalize donor name for comparison.

    Args:
        name: Donor name to normalize

    Returns:
        Normalized donor name with proper capitalization
    """
    if not name:
        return None
    # Clean and normalize
    name = str(name).strip()
    if not name:
        return None
    # Title case with special handling for apostrophes and hyphens
    words = []
    for word in name.split():
        if "'" in word:
            parts = word.split("'")
            word = "'".join(p.capitalize() for p in parts)
        elif "-" in word:
            parts = word.split("-")
            word = "-".join(p.capitalize() for p in parts)
        else:
            word = word.capitalize()
        words.append(word)
    return " ".join(words)


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    Normalize date string to consistent format.

    Args:
        date_str: Date string to normalize

    Returns:
        Normalized date in YYYY-MM-DD format, or None if parsing fails
    """
    if not date_str:
        return None
    try:
        # Try to parse various date formats
        parsed_date = dateutil.parser.parse(str(date_str))
        return parsed_date.strftime("%Y-%m-%d")
    except (ValueError, TypeError, dateutil.parser.ParserError):
        # If parsing fails, return None
        return None


def log_audit_event(
    event_type: str,
    user_id: Optional[str] = None,
    details: Optional[Dict] = None,
    request_ip: Optional[str] = None,
    audit_logger=None,
) -> Dict:
    """
    Log security and audit events.

    Args:
        event_type: Type of event (e.g., 'login', 'upload', 'qbo_auth')
        user_id: User identifier (if available)
        details: Additional event details
        request_ip: Client IP address
        audit_logger: Logger instance to use (optional)

    Returns:
        The audit event data that was logged
    """
    event_data = {
        "event_type": event_type,
        "user_id": user_id or "anonymous",
        "ip_address": request_ip or "unknown",
        "details": sanitize_for_logging(details) if details else {},
        "timestamp": datetime.now().isoformat(),
    }

    if audit_logger:
        audit_logger.info(json.dumps(event_data))

    return event_data
