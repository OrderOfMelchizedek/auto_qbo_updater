"""
Unit tests for the validation service module.
"""

import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from services.validation import (
    DATE_WARNING_DAYS,
    FUTURE_DATE_LIMIT_DAYS,
    log_audit_event,
    normalize_amount,
    normalize_check_number,
    normalize_date,
    normalize_donor_name,
    sanitize_for_logging,
    validate_donation_date,
    validate_environment,
)


class TestSanitizeForLogging:
    """Test the sanitize_for_logging function."""

    def test_sanitize_dict_with_sensitive_keys(self):
        """Test sanitizing dictionary with sensitive field names."""
        data = {
            "username": "john_doe",
            "password": "secret123",
            "api_key": "abc123xyz",
            "token": "bearer_token_123",
            "ssn": "123-45-6789",
            "normal_field": "normal_value",
        }

        result = sanitize_for_logging(data)

        assert result["username"] == "john_doe"
        assert result["password"] == "[REDACTED]"
        assert result["api_key"] == "[REDACTED]"
        assert result["token"] == "[REDACTED]"
        assert result["ssn"] == "[REDACTED]"
        assert result["normal_field"] == "normal_value"

    def test_sanitize_nested_dict(self):
        """Test sanitizing nested dictionaries."""
        data = {"user": {"name": "John", "credentials": {"password": "secret", "auth_token": "xyz123"}}}

        result = sanitize_for_logging(data)

        assert result["user"]["name"] == "John"
        assert result["user"]["credentials"]["password"] == "[REDACTED]"
        assert result["user"]["credentials"]["auth_token"] == "[REDACTED]"

    def test_sanitize_string_with_patterns(self):
        """Test sanitizing strings containing sensitive patterns."""
        # Long alphanumeric string (potential token)
        token_string = "Token: abcdef1234567890abcdef1234567890"
        result = sanitize_for_logging(token_string)
        assert "[REDACTED_TOKEN]" in result

        # SSN pattern
        ssn_string = "SSN: 123-45-6789"
        result = sanitize_for_logging(ssn_string)
        assert "[REDACTED_SSN]" in result

    def test_sanitize_list(self):
        """Test sanitizing lists containing dictionaries."""
        data = [{"name": "Item1", "secret": "value1"}, {"name": "Item2", "secret": "value2"}]

        result = sanitize_for_logging(data)

        assert isinstance(result, list)
        assert len(result) == 2


class TestValidateDonationDate:
    """Test the validate_donation_date function."""

    def test_valid_date(self):
        """Test validation of a normal date."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        is_valid, warning, parsed_date = validate_donation_date(date_str)

        assert is_valid is True
        assert warning is None
        assert parsed_date is not None

    def test_future_date_within_limit(self):
        """Test validation of future date within allowed limit."""
        future_date = datetime.now() + timedelta(days=15)
        date_str = future_date.strftime("%Y-%m-%d")

        is_valid, warning, parsed_date = validate_donation_date(date_str)

        assert is_valid is True
        assert warning is not None
        assert "15 days in the future" in warning
        assert parsed_date is not None

    def test_future_date_exceeds_limit(self):
        """Test validation of future date exceeding limit."""
        future_date = datetime.now() + timedelta(days=FUTURE_DATE_LIMIT_DAYS + 10)
        date_str = future_date.strftime("%Y-%m-%d")

        is_valid, warning, parsed_date = validate_donation_date(date_str)

        assert is_valid is False
        assert warning is not None
        assert f"max allowed: {FUTURE_DATE_LIMIT_DAYS} days" in warning
        assert parsed_date is None

    def test_old_date_with_warning(self):
        """Test validation of old date that triggers warning."""
        old_date = datetime.now() - timedelta(days=DATE_WARNING_DAYS + 100)
        date_str = old_date.strftime("%Y-%m-%d")

        is_valid, warning, parsed_date = validate_donation_date(date_str)

        assert is_valid is True
        assert warning is not None
        assert "years old" in warning
        assert parsed_date is not None

    def test_invalid_date_format(self):
        """Test validation of invalid date format."""
        is_valid, warning, parsed_date = validate_donation_date("not-a-date")

        assert is_valid is False
        assert warning is not None
        assert "Invalid" in warning
        assert parsed_date is None

    def test_empty_date(self):
        """Test validation of empty date string."""
        is_valid, warning, parsed_date = validate_donation_date("")

        assert is_valid is True
        assert warning is None
        assert parsed_date is None


class TestValidateEnvironment:
    """Test the validate_environment function."""

    def test_missing_required_variables(self):
        """Test validation fails when required variables are missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                validate_environment()

            error_msg = str(exc_info.value)
            assert "Missing required environment variables" in error_msg
            assert "FLASK_SECRET_KEY" in error_msg
            assert "GEMINI_API_KEY" in error_msg

    def test_all_required_variables_present(self):
        """Test validation passes when all required variables are present."""
        env_vars = {
            "FLASK_SECRET_KEY": "test_secret",
            "GEMINI_API_KEY": "test_api_key",
            "QBO_CLIENT_ID": "test_client_id",
            "QBO_CLIENT_SECRET": "test_client_secret",
            "QBO_REDIRECT_URI": "https://example.com/callback",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Should not raise any exception
            validate_environment()

    def test_invalid_qbo_environment(self):
        """Test validation fails for invalid QBO_ENVIRONMENT value."""
        env_vars = {
            "FLASK_SECRET_KEY": "test_secret",
            "GEMINI_API_KEY": "test_api_key",
            "QBO_CLIENT_ID": "test_client_id",
            "QBO_CLIENT_SECRET": "test_client_secret",
            "QBO_REDIRECT_URI": "https://example.com/callback",
            "QBO_ENVIRONMENT": "invalid_env",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError) as exc_info:
                validate_environment()

            assert "Invalid QBO_ENVIRONMENT" in str(exc_info.value)

    def test_invalid_redirect_uri(self):
        """Test validation fails for invalid redirect URI format."""
        env_vars = {
            "FLASK_SECRET_KEY": "test_secret",
            "GEMINI_API_KEY": "test_api_key",
            "QBO_CLIENT_ID": "test_client_id",
            "QBO_CLIENT_SECRET": "test_client_secret",
            "QBO_REDIRECT_URI": "not-a-valid-url",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError) as exc_info:
                validate_environment()

            assert "Invalid QBO_REDIRECT_URI" in str(exc_info.value)


class TestNormalizationFunctions:
    """Test the various normalization functions."""

    def test_normalize_check_number(self):
        """Test check number normalization."""
        assert normalize_check_number("0123") == "123"
        assert normalize_check_number("  456  ") == "456"
        assert normalize_check_number("000") == "0"
        assert normalize_check_number("") == ""
        assert normalize_check_number(None) == ""

    def test_normalize_amount(self):
        """Test amount normalization."""
        assert normalize_amount("$100.00") == "100.00"
        assert normalize_amount("1,234.56") == "1234.56"
        assert normalize_amount("  $50  ") == "50.00"
        assert normalize_amount(100) == "100.00"
        assert normalize_amount(100.5) == "100.50"
        assert normalize_amount("") == ""
        assert normalize_amount(None) == ""
        assert normalize_amount("invalid") == "invalid"

    def test_normalize_donor_name(self):
        """Test donor name normalization."""
        assert normalize_donor_name("John Doe") == "john doe"
        assert normalize_donor_name("JANE  SMITH") == "jane smith"
        assert normalize_donor_name("O'Brien, Pat") == "obrien pat"
        assert normalize_donor_name("  Test   Name  ") == "test name"
        assert normalize_donor_name("") == ""
        assert normalize_donor_name(None) == ""

    def test_normalize_date(self):
        """Test date normalization."""
        # Valid dates
        assert normalize_date("2024-01-15") == "2024-01-15"
        assert normalize_date("01/15/2024") == "2024-01-15"
        assert normalize_date("January 15, 2024") == "2024-01-15"

        # Invalid dates
        assert normalize_date("invalid-date") == "invalid-date"
        assert normalize_date("") == ""
        assert normalize_date(None) == ""


class TestLogAuditEvent:
    """Test the log_audit_event function."""

    def test_log_audit_event_basic(self):
        """Test basic audit event logging."""
        mock_logger = Mock()

        event_data = log_audit_event(
            event_type="test_event",
            user_id="user123",
            details={"action": "test_action"},
            request_ip="192.168.1.1",
            audit_logger=mock_logger,
        )

        assert event_data["event_type"] == "test_event"
        assert event_data["user_id"] == "user123"
        assert event_data["ip_address"] == "192.168.1.1"
        assert event_data["details"]["action"] == "test_action"
        assert "timestamp" in event_data

        # Check logger was called
        mock_logger.info.assert_called_once()

    def test_log_audit_event_with_defaults(self):
        """Test audit event logging with default values."""
        mock_logger = Mock()

        event_data = log_audit_event(event_type="test_event", audit_logger=mock_logger)

        assert event_data["user_id"] == "anonymous"
        assert event_data["ip_address"] == "unknown"
        assert event_data["details"] == {}

    def test_log_audit_event_sanitizes_details(self):
        """Test that audit event details are sanitized."""
        mock_logger = Mock()

        sensitive_details = {"action": "login", "password": "secret123", "token": "abc123"}

        event_data = log_audit_event(event_type="login", details=sensitive_details, audit_logger=mock_logger)

        # Check that sensitive data was sanitized
        assert event_data["details"]["action"] == "login"
        assert event_data["details"]["password"] == "[REDACTED]"
        assert event_data["details"]["token"] == "[REDACTED]"
