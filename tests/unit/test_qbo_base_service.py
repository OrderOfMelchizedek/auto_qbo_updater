"""
Unit tests for QBO Base Service module.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from src.utils.exceptions import QBOAPIException, RetryableException
from src.utils.qbo_service.auth import QBOAuthService
from src.utils.qbo_service.base import QBOBaseService


class TestQBOBaseService:
    """Test the QBO base service functionality."""

    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service."""
        mock = Mock(spec=QBOAuthService)
        mock.api_base = "https://sandbox-quickbooks.api.intuit.com/v3/company/"
        mock.realm_id = "test_realm_123"
        mock.get_auth_headers.return_value = {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        return mock

    @pytest.fixture
    def base_service(self, mock_auth_service):
        """Create a base service instance."""
        return QBOBaseService(mock_auth_service)

    def test_init(self, base_service, mock_auth_service):
        """Test base service initialization."""
        assert base_service.auth_service == mock_auth_service
        assert base_service.DEFAULT_TIMEOUT == 30

    def test_api_base_property(self, base_service, mock_auth_service):
        """Test api_base property delegates to auth service."""
        assert base_service.api_base == mock_auth_service.api_base

    def test_realm_id_property(self, base_service, mock_auth_service):
        """Test realm_id property delegates to auth service."""
        assert base_service.realm_id == mock_auth_service.realm_id

    def test_escape_query_value_simple(self, base_service):
        """Test escaping simple query values."""
        assert base_service._escape_query_value("simple") == "simple"
        assert base_service._escape_query_value("with space") == "with%20space"

    def test_escape_query_value_single_quotes(self, base_service):
        """Test escaping single quotes in query values."""
        assert base_service._escape_query_value("O'Brien") == "O%5C%27Brien"
        assert base_service._escape_query_value("It's a test") == "It%5C%27s%20a%20test"

    def test_escape_query_value_special_chars(self, base_service):
        """Test escaping special characters."""
        assert base_service._escape_query_value("test&value") == "test%26value"
        assert base_service._escape_query_value("test=value") == "test%3Dvalue"

    def test_escape_query_value_empty(self, base_service):
        """Test escaping empty or None values."""
        assert base_service._escape_query_value("") == ""
        assert base_service._escape_query_value(None) is None

    @patch("requests.request")
    def test_make_qbo_request_success(self, mock_request, base_service):
        """Test successful QBO API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Customer": {"Id": "123", "DisplayName": "Test"}}
        mock_request.return_value = mock_response

        result = base_service._make_qbo_request("GET", "customer/123")

        assert result == {"Customer": {"Id": "123", "DisplayName": "Test"}}
        mock_request.assert_called_once_with(
            method="GET",
            url="https://sandbox-quickbooks.api.intuit.com/v3/company/test_realm_123/customer/123",
            headers={
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=None,
            params=None,
            timeout=30,
        )

    @patch("requests.request")
    def test_make_qbo_request_with_data(self, mock_request, base_service):
        """Test QBO API request with POST data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"Customer": {"Id": "123"}}
        mock_request.return_value = mock_response

        data = {"DisplayName": "New Customer"}
        result = base_service._make_qbo_request("POST", "customer", data=data)

        assert result == {"Customer": {"Id": "123"}}
        mock_request.assert_called_once_with(
            method="POST",
            url="https://sandbox-quickbooks.api.intuit.com/v3/company/test_realm_123/customer",
            headers={
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=data,
            params=None,
            timeout=30,
        )

    def test_make_qbo_request_no_realm_id(self, base_service):
        """Test request fails when no realm ID is set."""
        base_service.auth_service.realm_id = None

        with pytest.raises(QBOAPIException) as exc_info:
            base_service._make_qbo_request("GET", "customer/123")

        assert "No realm ID set" in str(exc_info.value)
        assert "company not selected" in exc_info.value.user_message

    @patch("requests.request")
    def test_make_qbo_request_401_refresh_success(self, mock_request, base_service):
        """Test 401 response triggers token refresh and retry."""
        # First request returns 401
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        mock_response_401.text = "Unauthorized"

        # Second request after refresh succeeds
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"success": True}

        mock_request.side_effect = [mock_response_401, mock_response_success]
        base_service.auth_service.refresh_access_token.return_value = True

        # The retry decorator should handle the retry, so we expect success
        result = base_service._make_qbo_request("GET", "test")

        assert result == {"success": True}
        base_service.auth_service.refresh_access_token.assert_called_once()
        # Should be called twice - once for 401, once for successful retry
        assert mock_request.call_count == 2

    @patch("requests.request")
    def test_make_qbo_request_401_refresh_failure(self, mock_request, base_service):
        """Test 401 response when token refresh fails."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response

        base_service.auth_service.refresh_access_token.return_value = False

        with pytest.raises(QBOAPIException) as exc_info:
            base_service._make_qbo_request("GET", "test")

        assert exc_info.value.status_code == 401
        assert "Authentication failed" in str(exc_info.value)
        assert "reconnect to QuickBooks" in exc_info.value.user_message

    @patch("requests.request")
    def test_make_qbo_request_429_rate_limit(self, mock_request, base_service):
        """Test 429 rate limit response is retryable."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_request.return_value = mock_response

        with pytest.raises(RetryableException) as exc_info:
            base_service._make_qbo_request("GET", "test")

        assert "Rate limited" in str(exc_info.value)

    @patch("requests.request")
    def test_make_qbo_request_403_subscription(self, mock_request, base_service):
        """Test 403 response for subscription issues."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Your subscription has expired"
        mock_request.return_value = mock_response

        with pytest.raises(QBOAPIException) as exc_info:
            base_service._make_qbo_request("GET", "test")

        assert exc_info.value.status_code == 403
        assert "subscription" in exc_info.value.user_message.lower()

    @patch("requests.request")
    def test_make_qbo_request_403_permission(self, mock_request, base_service):
        """Test 403 response for permission issues."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Access denied"
        mock_request.return_value = mock_response

        with pytest.raises(QBOAPIException) as exc_info:
            base_service._make_qbo_request("GET", "test")

        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.user_message

    @patch("requests.request")
    def test_make_qbo_request_404_not_found(self, mock_request, base_service):
        """Test 404 not found response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Resource not found"
        mock_request.return_value = mock_response

        with pytest.raises(QBOAPIException) as exc_info:
            base_service._make_qbo_request("GET", "customer/999")

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.user_message

    @patch("requests.request")
    def test_make_qbo_request_400_bad_request(self, mock_request, base_service):
        """Test 400 bad request with error parsing."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = '{"Fault": {"Error": [{"Detail": "Invalid field value", "Message": "Bad request"}]}}'
        mock_response.json.return_value = {
            "Fault": {"Error": [{"Detail": "Invalid field value", "Message": "Bad request"}]}
        }
        mock_request.return_value = mock_response

        with pytest.raises(QBOAPIException) as exc_info:
            base_service._make_qbo_request("POST", "customer", data={})

        assert exc_info.value.status_code == 400
        assert "Invalid field value" in exc_info.value.user_message

    @patch("requests.request")
    def test_make_qbo_request_network_error(self, mock_request, base_service):
        """Test network error handling."""
        mock_request.side_effect = requests.RequestException("Connection timeout")

        with pytest.raises(RetryableException) as exc_info:
            base_service._make_qbo_request("GET", "test")

        assert "Network error" in str(exc_info.value)

    @patch("requests.request")
    def test_make_qbo_request_unexpected_error(self, mock_request, base_service):
        """Test unexpected error handling."""
        mock_request.side_effect = ValueError("Unexpected error")

        with pytest.raises(QBOAPIException) as exc_info:
            base_service._make_qbo_request("GET", "test")

        assert "Unexpected error" in str(exc_info.value)
        assert "unexpected error occurred" in exc_info.value.user_message

    def test_extract_error_message_fault_error_list(self, base_service):
        """Test extracting error message from Fault.Error list."""
        error_data = {"Fault": {"Error": [{"Detail": "Specific error detail", "Message": "General message"}]}}

        message = base_service._extract_error_message(error_data)
        assert message == "Specific error detail"

    def test_extract_error_message_fault_error_dict(self, base_service):
        """Test extracting error message from Fault.Error dict."""
        error_data = {"Fault": {"Error": {"Detail": "Error detail", "Message": "Error message"}}}

        message = base_service._extract_error_message(error_data)
        assert message == "Error detail"

    def test_extract_error_message_no_detail(self, base_service):
        """Test extracting error message when no Detail field."""
        error_data = {"Fault": {"Error": [{"Message": "Error message only"}]}}

        message = base_service._extract_error_message(error_data)
        assert message == "Error message only"

    def test_extract_error_message_invalid_structure(self, base_service):
        """Test extracting error message from invalid structure."""
        error_data = "Simple error string"

        message = base_service._extract_error_message(error_data)
        assert message == "Simple error string"

    @patch("requests.request")
    def test_make_qbo_request_with_custom_timeout(self, mock_request, base_service):
        """Test request with custom timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_request.return_value = mock_response

        base_service._make_qbo_request("GET", "test", timeout=60)

        # Should use custom timeout
        _, kwargs = mock_request.call_args
        assert kwargs["timeout"] == 60

    @patch("requests.request")
    def test_make_qbo_request_with_query_params(self, mock_request, base_service):
        """Test request with query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_request.return_value = mock_response

        params = {"startPosition": 1, "maxResults": 100}
        base_service._make_qbo_request("GET", "query", params=params)

        # Should pass params
        _, kwargs = mock_request.call_args
        assert kwargs["params"] == params
