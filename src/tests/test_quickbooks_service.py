"""Tests for QuickBooks service module."""
from unittest.mock import MagicMock, patch

import pytest

from src.quickbooks_service import QuickBooksClient, QuickBooksError


class TestQuickBooksClient:
    """Test QuickBooks API client."""

    @pytest.fixture
    def mock_auth(self):
        """Mock QuickBooks auth with tokens."""
        with patch("src.quickbooks_service.QuickBooksAuth") as mock:
            auth_instance = MagicMock()
            auth_instance.get_valid_access_token.return_value = "fake-access-token"
            auth_instance.get_auth_status.return_value = {
                "authenticated": True,
                "realm_id": "123456789",
            }
            mock.return_value = auth_instance
            yield auth_instance

    @pytest.fixture
    def client(self, mock_auth):
        """Create QuickBooks client with mocked auth."""
        return QuickBooksClient(session_id="test-session")

    @pytest.fixture
    def sample_customer_response(self):
        """Sample customer data from QuickBooks API."""
        return {
            "Customer": {
                "Id": "1",
                "DisplayName": "John Smith",
                "GivenName": "John",
                "FamilyName": "Smith",
                "CompanyName": None,
                "BillAddr": {
                    "Line1": "123 Main St",
                    "City": "Springfield",
                    "CountrySubDivisionCode": "CA",
                    "PostalCode": "94025",
                },
                "PrimaryEmailAddr": {"Address": "john@example.com"},
                "PrimaryPhone": {"FreeFormNumber": "555-1234"},
            }
        }

    @pytest.fixture
    def sample_org_customer_response(self):
        """Sample organization customer from QuickBooks."""
        return {
            "Customer": {
                "Id": "2",
                "DisplayName": "Smith Foundation",
                "CompanyName": "Smith Foundation",
                "GivenName": None,
                "FamilyName": None,
                "BillAddr": {
                    "Line1": "456 Corporate Blvd",
                    "City": "San Francisco",
                    "CountrySubDivisionCode": "CA",
                    "PostalCode": "94105",
                },
                "PrimaryEmailAddr": {"Address": "info@smithfoundation.org"},
            }
        }

    def test_client_initialization(self, client, mock_auth):
        """Test client initializes with auth."""
        assert client.session_id == "test-session"
        assert client.auth is not None
        assert (
            client.base_url
            == "https://sandbox-quickbooks.api.intuit.com/v3/company/123456789"
        )

    def test_client_initialization_production(self, mock_auth):
        """Test client uses production URL when configured."""
        with patch("src.quickbooks_service.Config.QBO_ENVIRONMENT", "production"):
            client = QuickBooksClient(session_id="test-session")
            assert (
                client.base_url
                == "https://quickbooks.api.intuit.com/v3/company/123456789"
            )

    @patch("requests.request")
    def test_search_customer_by_name(
        self, mock_request, client, sample_customer_response
    ):
        """Test searching for customer by name."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "QueryResponse": {"Customer": [sample_customer_response["Customer"]]}
        }
        mock_request.return_value = mock_response

        # Search for customer
        results = client.search_customer("John Smith")

        # Verify API call
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "/query" in call_args[0][1]
        assert call_args[0][0] == "GET"
        assert "DisplayName" in call_args[1]["params"]["query"]
        assert "John Smith" in call_args[1]["params"]["query"]
        assert call_args[1]["headers"]["Authorization"] == "Bearer fake-access-token"

        # Verify results
        assert len(results) == 1
        assert results[0]["DisplayName"] == "John Smith"

    @patch("requests.request")
    def test_search_customer_no_results(self, mock_request, client):
        """Test searching when no customers found."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"QueryResponse": {}}
        mock_request.return_value = mock_response

        results = client.search_customer("Nonexistent Person")
        assert results == []

    @patch("requests.request")
    def test_search_customer_multiple_results(self, mock_request, client):
        """Test searching returns multiple matches."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "QueryResponse": {
                "Customer": [
                    {"Id": "1", "DisplayName": "John Smith"},
                    {"Id": "2", "DisplayName": "John Smith Jr"},
                    {"Id": "3", "DisplayName": "Smith, John"},
                ]
            }
        }
        mock_request.return_value = mock_response

        results = client.search_customer("John Smith")
        assert len(results) == 3

    @patch("requests.request")
    def test_search_customer_api_error(self, mock_request, client):
        """Test handling API errors during search."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response

        with pytest.raises(QuickBooksError) as exc_info:
            client.search_customer("John Smith")
        assert "401" in str(exc_info.value)

    @patch("requests.request")
    def test_get_customer(self, mock_request, client, sample_customer_response):
        """Test retrieving full customer details."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_customer_response
        mock_request.return_value = mock_response

        customer = client.get_customer("1")

        # Verify API call
        mock_request.assert_called_once()
        assert "/customer/1" in mock_request.call_args[0][1]

        # Verify response
        assert customer["Id"] == "1"
        assert customer["DisplayName"] == "John Smith"

    @patch("requests.request")
    def test_get_customer_not_found(self, mock_request, client):
        """Test handling when customer not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Customer not found"
        mock_request.return_value = mock_response

        with pytest.raises(QuickBooksError) as exc_info:
            client.get_customer("999")
        assert "404" in str(exc_info.value)

    def test_format_customer_data_individual(self, client, sample_customer_response):
        """Test formatting individual customer data to PRD structure."""
        customer = sample_customer_response["Customer"]
        formatted = client.format_customer_data(customer)

        expected = {
            "customer_ref": {
                "id": "1",
                "first_name": "John",
                "last_name": "Smith",
                "full_name": "John Smith",
                "company_name": None,
            },
            "qb_address": {
                "line1": "123 Main St",
                "city": "Springfield",
                "state": "CA",
                "zip": "94025",
            },
            "qb_email": ["john@example.com"],
            "qb_phone": ["555-1234"],
        }

        assert formatted == expected

    def test_format_customer_data_organization(
        self, client, sample_org_customer_response
    ):
        """Test formatting organization customer data."""
        customer = sample_org_customer_response["Customer"]
        formatted = client.format_customer_data(customer)

        expected = {
            "customer_ref": {
                "id": "2",
                "first_name": None,
                "last_name": None,
                "full_name": "Smith Foundation",
                "company_name": "Smith Foundation",
            },
            "qb_address": {
                "line1": "456 Corporate Blvd",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94105",
            },
            "qb_email": ["info@smithfoundation.org"],
            "qb_phone": [],
        }

        assert formatted == expected

    def test_format_customer_data_missing_fields(self, client):
        """Test formatting with missing optional fields."""
        customer = {
            "Id": "3",
            "DisplayName": "Jane Doe",
            "GivenName": "Jane",
            "FamilyName": "Doe"
            # No address, email, or phone
        }
        formatted = client.format_customer_data(customer)

        assert formatted["customer_ref"]["full_name"] == "Jane Doe"
        assert formatted["qb_address"]["line1"] == ""
        assert formatted["qb_email"] == []
        assert formatted["qb_phone"] == []

    def test_format_customer_data_zip_with_extension(self, client):
        """Test ZIP code formatting removes +4 extension."""
        customer = {
            "Id": "4",
            "DisplayName": "Test User",
            "BillAddr": {"PostalCode": "94025-1234"},
        }
        formatted = client.format_customer_data(customer)
        assert formatted["qb_address"]["zip"] == "94025"

    def test_format_customer_data_preserves_leading_zeros(self, client):
        """Test ZIP code preserves leading zeros."""
        customer = {
            "Id": "5",
            "DisplayName": "East Coast User",
            "BillAddr": {"PostalCode": "00501"},
        }
        formatted = client.format_customer_data(customer)
        assert formatted["qb_address"]["zip"] == "00501"

    @patch("requests.request")
    def test_token_refresh_on_401(self, mock_request, client, mock_auth):
        """Test automatic token refresh on 401 error."""
        # First call returns 401
        mock_response_401 = MagicMock()
        mock_response_401.status_code = 401

        # Second call succeeds after refresh
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"QueryResponse": {}}

        mock_request.side_effect = [mock_response_401, mock_response_200]
        mock_auth.refresh_access_token.return_value = {
            "success": True,
            "expires_at": "2024-01-01T00:00:00Z",
        }

        # Should not raise exception
        client.search_customer("Test")

        # Verify token refresh was called
        mock_auth.refresh_access_token.assert_called_once()
        assert mock_request.call_count == 2

    # Tests for create_customer method
    def test_create_customer_success(self, client, mock_auth):
        """Test successful customer creation via QuickBooksClient."""
        mock_response_data = {
            "Customer": {"Id": "123", "DisplayName": "New Test Customer"}
        }
        mock_api_response = MagicMock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = mock_response_data

        # Patch _make_request for this specific client instance
        with patch.object(
            client, "_make_request", return_value=mock_api_response
        ) as mock_make_request:
            customer_data_input = {
                "DisplayName": "New Test Customer",
                "GivenName": "New",
                "FamilyName": "Test",
                "PrimaryEmailAddr": "new@example.com",
                "PrimaryPhone": "123-456-7890",
                "BillAddr": {
                    "Line1": "123 New St",
                    "City": "Newville",
                    "CountrySubDivisionCode": "NY",
                    "PostalCode": "10001",
                },
            }

            expected_payload = {
                "DisplayName": "New Test Customer",
                "GivenName": "New",
                "FamilyName": "Test",
                "PrimaryEmailAddr": {"Address": "new@example.com"},
                "PrimaryPhone": {"FreeFormNumber": "123-456-7890"},
                "BillAddr": {
                    "Line1": "123 New St",
                    "City": "Newville",
                    "CountrySubDivisionCode": "NY",
                    "PostalCode": "10001",
                },
            }

            created_customer = client.create_customer(customer_data=customer_data_input)

            mock_make_request.assert_called_once_with(
                "POST", "/customer", json=expected_payload
            )
            assert created_customer == mock_response_data["Customer"]

    def test_create_customer_missing_display_name(self, client):
        """Test create_customer raises ValueError if DisplayName is missing."""
        with pytest.raises(ValueError) as exc_info:
            client.create_customer(customer_data={"GivenName": "Test"})
        assert "DisplayName is required" in str(exc_info.value)

    def test_create_customer_api_error(self, client, mock_auth):
        """Test create_customer propagates QuickBooksError from _make_request."""
        with patch.object(
            client, "_make_request", side_effect=QuickBooksError("API failure")
        ) as mock_make_request:
            with pytest.raises(QuickBooksError) as exc_info:
                client.create_customer(customer_data={"DisplayName": "Error Case"})
            assert "API failure" in str(exc_info.value)
            mock_make_request.assert_called_once()

    def test_create_customer_payload_construction_minimal(self, client, mock_auth):
        """Test payload construction with only DisplayName."""
        mock_api_response = MagicMock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = {
            "Customer": {"Id": "1", "DisplayName": "Minimal Customer"}
        }

        with patch.object(
            client, "_make_request", return_value=mock_api_response
        ) as mock_make_request:
            customer_data_input = {"DisplayName": "Minimal Customer"}
            expected_payload = {"DisplayName": "Minimal Customer"}

            client.create_customer(customer_data=customer_data_input)
            mock_make_request.assert_called_once_with(
                "POST", "/customer", json=expected_payload
            )

    def test_create_customer_payload_construction_optional_fields_none(
        self, client, mock_auth
    ):
        """Test payload construction when optional fields are None or empty string."""
        mock_api_response = MagicMock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = {
            "Customer": {"Id": "1", "DisplayName": "Optional None"}
        }

        with patch.object(
            client, "_make_request", return_value=mock_api_response
        ) as mock_make_request:
            customer_data_input = {
                "DisplayName": "Optional None",
                "GivenName": None,  # Should be excluded from payload
                "FamilyName": "",  # Should be excluded from payload
                "PrimaryEmailAddr": None,  # Should be excluded
                "BillAddr": {
                    "Line1": None,
                    "City": "",
                },  # Should be excluded if all sub-fields are None/empty
            }
            # The create_customer method filters out None values,
            # so the payload would be minimal
            client.create_customer(customer_data=customer_data_input)
            # The key is that `PrimaryEmailAddr` (if None) is not
            # turned into `{"Address": None}` and then filtered.
            # It's simply not added if
            # `customer_data.get("PrimaryEmailAddr")` is falsy.

            # Test with empty strings
            customer_data_input_strict = {
                "DisplayName": "Optional None",
                "FamilyName": "",  # Empty string
                "BillAddr": {"City": ""},  # Partially empty
            }
            expected_payload_strict = {
                "DisplayName": "Optional None",
                "FamilyName": "",  # Empty string included
                "BillAddr": {"City": ""},  # Included with empty city
            }
            client.create_customer(customer_data=customer_data_input_strict)
            mock_make_request.assert_called_with(
                "POST", "/customer", json=expected_payload_strict
            )
