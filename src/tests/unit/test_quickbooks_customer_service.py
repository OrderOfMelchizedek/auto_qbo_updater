"""Tests for QuickBooks customer service."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.models.donation import Address, ContactInfo, PayerInfo
from src.models.quickbooks import CustomerMatch, QuickBooksCustomer
from src.services.quickbooks.customer_service import CustomerService
from src.utils.exceptions import QuickBooksIntegrationError


@pytest.fixture
def mock_oauth_token():
    """Mock OAuth token."""
    return {
        "access_token": "mock_access_token",
        "realm_id": "123456789",
        "refresh_token": "mock_refresh_token",
    }


@pytest.fixture
def mock_oauth_session():
    """Mock OAuth session."""
    with patch("src.services.quickbooks.customer_service.OAuth2Session") as mock:
        session = MagicMock()
        mock.return_value = session
        yield session


@pytest.fixture
def customer_service(mock_oauth_token, mock_oauth_session):
    """Create customer service instance."""
    return CustomerService(mock_oauth_token)


@pytest.fixture
def sample_payer_info():
    """Sample payer information."""
    return PayerInfo(
        name="John Smith",
        organization="Smith Foundation",
        aliases=["J. Smith", "John S."],
    )


@pytest.fixture
def sample_contact_info():
    """Sample contact information."""
    return ContactInfo(
        email="john.smith@example.com",
        phone="(555) 123-4567",
        address=Address(
            street1="123 Main St",
            city="San Francisco",
            state="CA",
            postal_code="94105",
        ),
    )


@pytest.fixture
def sample_customer_response():
    """Sample QuickBooks customer response."""
    return {
        "Id": "123",
        "SyncToken": "0",
        "DisplayName": "John Smith",
        "CompanyName": "Smith Foundation",
        "GivenName": "John",
        "FamilyName": "Smith",
        "PrimaryEmailAddr": {"Address": "john.smith@example.com"},
        "PrimaryPhone": {"FreeFormNumber": "(555) 123-4567"},
        "BillAddr": {
            "Line1": "123 Main St",
            "City": "San Francisco",
            "CountrySubDivisionCode": "CA",
            "PostalCode": "94105",
        },
        "Active": True,
        "Balance": 0,
    }


class TestCustomerService:
    """Test QuickBooks customer service."""

    def test_search_customers_success(
        self,
        customer_service,
        mock_oauth_session,
        sample_payer_info,
        sample_contact_info,
        sample_customer_response,
    ):
        """Test successful customer search."""
        # Mock query response
        mock_oauth_session.get.return_value.json.return_value = {
            "QueryResponse": {"Customer": [sample_customer_response]}
        }
        mock_oauth_session.get.return_value.raise_for_status = MagicMock()

        # Search customers
        matches = customer_service.search_customers(
            sample_payer_info, sample_contact_info
        )

        # Verify results
        assert len(matches) > 0
        assert isinstance(matches[0], CustomerMatch)
        assert matches[0].customer_id == "123"
        assert matches[0].display_name == "John Smith"
        assert matches[0].confidence_score > 0

        # Verify API calls
        assert mock_oauth_session.get.called

    def test_search_customers_no_matches(
        self, customer_service, mock_oauth_session, sample_payer_info
    ):
        """Test customer search with no matches."""
        # Mock empty response
        mock_oauth_session.get.return_value.json.return_value = {
            "QueryResponse": {"Customer": []}
        }
        mock_oauth_session.get.return_value.raise_for_status = MagicMock()

        # Search customers
        matches = customer_service.search_customers(sample_payer_info)

        # Verify empty results
        assert len(matches) == 0

    def test_search_customers_api_error(
        self, customer_service, mock_oauth_session, sample_payer_info
    ):
        """Test customer search with API error."""
        # Mock API error
        mock_oauth_session.get.side_effect = requests.RequestException("API Error")

        # When all queries fail, it should return empty list (not raise exception)
        matches = customer_service.search_customers(sample_payer_info)

        # Verify empty results due to failed queries
        assert len(matches) == 0

    def test_get_customer_success(
        self, customer_service, mock_oauth_session, sample_customer_response
    ):
        """Test getting customer by ID."""
        # Mock response
        mock_oauth_session.get.return_value.json.return_value = {
            "Customer": sample_customer_response
        }
        mock_oauth_session.get.return_value.raise_for_status = MagicMock()

        # Get customer
        customer = customer_service.get_customer("123")

        # Verify result
        assert isinstance(customer, QuickBooksCustomer)
        assert customer.id == "123"
        assert customer.display_name == "John Smith"

    def test_create_customer_success(
        self,
        customer_service,
        mock_oauth_session,
        sample_payer_info,
        sample_contact_info,
        sample_customer_response,
    ):
        """Test creating a new customer."""
        # Mock response
        mock_oauth_session.post.return_value.json.return_value = {
            "Customer": sample_customer_response
        }
        mock_oauth_session.post.return_value.raise_for_status = MagicMock()

        # Create customer
        customer = customer_service.create_customer(
            sample_payer_info, sample_contact_info
        )

        # Verify result
        assert isinstance(customer, QuickBooksCustomer)
        assert customer.display_name == "John Smith"

        # Verify API call
        mock_oauth_session.post.assert_called_once()
        call_args = mock_oauth_session.post.call_args
        assert "customer" in call_args[0][0]

        # Verify request data
        request_data = call_args[1]["json"]
        assert request_data["DisplayName"] == "John Smith"
        assert request_data["CompanyName"] == "Smith Foundation"
        assert request_data["PrimaryEmailAddr"]["Address"] == "john.smith@example.com"

    def test_create_customer_api_error(
        self, customer_service, mock_oauth_session, sample_payer_info
    ):
        """Test customer creation with API error."""
        # Mock API error
        mock_oauth_session.post.side_effect = requests.RequestException("API Error")

        # Verify exception
        with pytest.raises(QuickBooksIntegrationError) as exc:
            customer_service.create_customer(sample_payer_info)

        assert "Customer creation failed" in str(exc.value)

    def test_name_matching_exact(self, customer_service, sample_payer_info):
        """Test exact name matching."""
        customer = {"DisplayName": "John Smith"}
        score, _ = customer_service._score_name_match(customer, sample_payer_info)
        assert score == 1.0

    def test_name_matching_partial(self, customer_service, sample_payer_info):
        """Test partial name matching."""
        customer = {"DisplayName": "Smith, John"}
        score, _ = customer_service._score_name_match(customer, sample_payer_info)
        assert score > 0.5

    def test_name_matching_alias(self, customer_service, sample_payer_info):
        """Test alias matching."""
        customer = {"DisplayName": "J. Smith"}
        score, _ = customer_service._score_name_match(customer, sample_payer_info)
        assert score >= 0.9

    def test_email_matching(self, customer_service):
        """Test email matching."""
        customer = {"PrimaryEmailAddr": {"Address": "john.smith@example.com"}}
        score = customer_service._score_email_match(customer, "john.smith@example.com")
        assert score == 1.0

    def test_address_matching(self, customer_service, sample_contact_info):
        """Test address matching."""
        customer = {
            "BillAddr": {
                "PostalCode": "94105",
                "City": "San Francisco",
                "CountrySubDivisionCode": "CA",
            }
        }
        score = customer_service._score_address_match(customer, sample_contact_info)
        assert score == 1.0  # Perfect match

    def test_phone_matching(self, customer_service):
        """Test phone matching."""
        customer = {"PrimaryPhone": {"FreeFormNumber": "(555) 123-4567"}}
        score = customer_service._score_phone_match(customer, "555-123-4567")
        assert score == 1.0

    def test_deduplicate_and_score_matches(
        self, customer_service, sample_payer_info, sample_contact_info
    ):
        """Test deduplication and scoring of matches."""
        # Create duplicate matches
        matches = [
            {"Id": "123", "DisplayName": "John Smith"},
            {"Id": "123", "DisplayName": "John Smith"},  # Duplicate
            {"Id": "456", "DisplayName": "J. Smith"},
        ]

        # Deduplicate and score
        unique_matches = customer_service._deduplicate_and_score_matches(
            matches, sample_payer_info, sample_contact_info
        )

        # Verify deduplication
        assert len(unique_matches) == 2
        assert unique_matches[0].customer_id == "123"
        assert unique_matches[1].customer_id == "456"
