"""
Unit tests for QBO Customer Service module.
"""

import threading
from datetime import datetime
from unittest.mock import Mock, call, patch

import pytest

from src.utils.qbo_service.customers import QBOCustomerService


class TestQBOCustomerService:
    """Test the QBO customer service functionality."""

    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service."""
        mock = Mock()
        mock.is_token_valid.return_value = True
        mock.api_base = "https://sandbox-quickbooks.api.intuit.com/v3/company/"
        mock.realm_id = "test_realm_123"
        return mock

    @pytest.fixture
    def customer_service(self, mock_auth_service):
        """Create a customer service instance."""
        service = QBOCustomerService(mock_auth_service)
        # Clear any cache
        service._customer_cache.clear()
        service._cache_timestamp = None
        return service

    @pytest.fixture
    def sample_customer(self):
        """Create a sample customer."""
        return {
            "Id": "123",
            "DisplayName": "John Doe",
            "GivenName": "John",
            "FamilyName": "Doe",
            "PrimaryEmailAddr": {"Address": "john@example.com"},
            "Active": True,
        }

    def test_init(self, customer_service):
        """Test customer service initialization."""
        assert isinstance(customer_service._customer_cache, dict)
        assert customer_service._cache_timestamp is None
        assert isinstance(customer_service._cache_lock, type(threading.Lock()))
        assert customer_service._cache_ttl == 300  # 5 minutes

    def test_find_customer_not_authenticated(self, customer_service):
        """Test find customer when not authenticated."""
        customer_service.auth_service.is_token_valid.return_value = False

        result = customer_service.find_customer("John Doe")

        assert result is None

    def test_find_customer_empty_lookup(self, customer_service):
        """Test find customer with empty lookup value."""
        assert customer_service.find_customer("") is None
        assert customer_service.find_customer("   ") is None
        assert customer_service.find_customer(None) is None

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_find_customer_exact_match(self, mock_request, customer_service, sample_customer):
        """Test find customer with exact DisplayName match."""
        mock_request.return_value = {"QueryResponse": {"Customer": [sample_customer]}}

        result = customer_service.find_customer("John Doe")

        assert result == sample_customer
        # Should only make one request (exact match found)
        assert mock_request.call_count == 1
        # Check the query is properly encoded
        call_args = mock_request.call_args[0]
        assert "query?query=" in call_args[1]
        assert "DisplayName" in call_args[1]

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_find_customer_partial_match(self, mock_request, customer_service, sample_customer):
        """Test find customer with partial DisplayName match."""
        # First call (exact match) returns empty
        # Second call (partial match) returns customer
        mock_request.side_effect = [
            {"QueryResponse": {}},  # No exact match
            {"QueryResponse": {"Customer": [sample_customer]}},  # Partial match found
        ]

        result = customer_service.find_customer("John")

        assert result == sample_customer
        assert mock_request.call_count == 2
        # Check second query uses LIKE (encoded in URL)
        second_call = mock_request.call_args_list[1][0]
        assert "query?query=" in second_call[1]
        assert "LIKE" in second_call[1]

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_find_customer_reversed_name(self, mock_request, customer_service, sample_customer):
        """Test find customer with reversed name (Last, First)."""
        # Track all queries made
        queries_made = []

        def mock_response(method, endpoint, **kwargs):
            queries_made.append(endpoint)
            # Check if this is a LIKE query containing both "Smith" and "John"
            if "query?query=" in endpoint and "LIKE" in endpoint:
                # Check for "Smith, John" pattern (URL encoded)
                if "Smith" in endpoint and "John" in endpoint:
                    return {"QueryResponse": {"Customer": [sample_customer]}}
            return {"QueryResponse": {}}

        mock_request.side_effect = mock_response

        result = customer_service.find_customer("John Smith")

        assert result == sample_customer
        # Should have tried multiple strategies including reversed name
        assert mock_request.call_count >= 1
        # Verify it tried the reversed name strategy
        assert any("Smith" in q and "John" in q for q in queries_made)

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_find_customer_comma_to_space(self, mock_request, customer_service, sample_customer):
        """Test find customer converting comma-separated to space-separated."""
        # Track all queries made
        queries_made = []

        def mock_response(method, endpoint, **kwargs):
            queries_made.append(endpoint)
            # Check if this is a LIKE query for "John Smith" (space-separated conversion)
            if "query?query=" in endpoint and "LIKE" in endpoint:
                # The code converts "Smith, John" to "John Smith"
                if "John" in endpoint and "Smith" in endpoint and "%2C" not in endpoint:
                    return {"QueryResponse": {"Customer": [sample_customer]}}
            return {"QueryResponse": {}}

        mock_request.side_effect = mock_response

        result = customer_service.find_customer("Smith, John")

        assert result == sample_customer
        # Should have tried multiple strategies
        assert mock_request.call_count >= 1
        # Verify it tried the comma-to-space conversion
        assert any("John" in q and "Smith" in q and "%2C" not in q for q in queries_made)

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_find_customer_significant_parts(self, mock_request, customer_service, sample_customer):
        """Test find customer using significant parts matching."""
        mock_request.side_effect = [
            {"QueryResponse": {}},  # No exact match
            {"QueryResponse": {}},  # No partial match
            {"QueryResponse": {"Customer": [sample_customer]}},  # Significant part match
        ]

        result = customer_service.find_customer("Mr. John and Jane Smith")

        assert result == sample_customer
        # Should try to match on significant parts like "Smith"
        assert mock_request.call_count >= 3

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_find_customer_email_domain(self, mock_request, customer_service, sample_customer):
        """Test find customer by email domain."""
        # Create customer with org name
        org_customer = sample_customer.copy()
        org_customer["DisplayName"] = "Example Organization"

        # Track all queries made
        queries_made = []

        def mock_response(method, endpoint, **kwargs):
            queries_made.append(endpoint)
            # Check if this is a LIKE query containing "example" (from email domain)
            if "query?query=" in endpoint and "LIKE" in endpoint and "example" in endpoint:
                return {"QueryResponse": {"Customer": [org_customer]}}
            return {"QueryResponse": {}}

        mock_request.side_effect = mock_response

        result = customer_service.find_customer("contact@example.org")

        assert result == org_customer
        # Should have tried multiple strategies before reaching email domain strategy
        assert mock_request.call_count >= 1
        # Verify it tried the email domain strategy
        assert any("example" in q for q in queries_made)

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_find_customer_phone_number(self, mock_request, customer_service, sample_customer):
        """Test find customer by phone number."""
        # Track all queries made
        queries_made = []

        def mock_response(method, endpoint, **kwargs):
            queries_made.append(endpoint)
            # Check if this is a phone query (last 7 digits)
            if "query?query=" in endpoint and "PrimaryPhone" in endpoint and "1234567" in endpoint:
                return {"QueryResponse": {"Customer": [sample_customer]}}
            return {"QueryResponse": {}}

        mock_request.side_effect = mock_response

        result = customer_service.find_customer("555-123-4567")

        assert result == sample_customer
        # Should have tried multiple strategies before phone search
        assert mock_request.call_count >= 1
        # Verify it tried the phone strategy
        assert any("PrimaryPhone" in q and "1234567" in q for q in queries_made)

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_find_customer_no_match(self, mock_request, customer_service):
        """Test find customer with no matches."""
        # All strategies return empty
        mock_request.return_value = {"QueryResponse": {}}

        result = customer_service.find_customer("Nonexistent Customer")

        assert result is None

    def test_find_customer_cached(self, customer_service, sample_customer):
        """Test find customer returns cached result."""
        # Populate cache
        customer_service._customer_cache["john doe"] = sample_customer
        customer_service._cache_timestamp = datetime.now().timestamp()

        with patch.object(customer_service, "_make_qbo_request") as mock_request:
            result = customer_service.find_customer("John Doe")

        assert result == sample_customer
        # Should not make any API requests
        mock_request.assert_not_called()

    def test_find_customer_cache_expired(self, customer_service, sample_customer):
        """Test find customer when cache is expired."""
        # Populate expired cache
        customer_service._customer_cache["john doe"] = sample_customer
        customer_service._cache_timestamp = datetime.now().timestamp() - 400  # Expired

        with patch.object(customer_service, "_make_qbo_request") as mock_request:
            mock_request.return_value = {"QueryResponse": {"Customer": [sample_customer]}}

            result = customer_service.find_customer("John Doe")

        assert result == sample_customer
        # Should make API request due to expired cache
        mock_request.assert_called()

    def test_find_customers_batch_empty(self, customer_service):
        """Test batch find with empty list."""
        result = customer_service.find_customers_batch([])
        assert result == {}

    def test_find_customers_batch_not_authenticated(self, customer_service):
        """Test batch find when not authenticated."""
        customer_service.auth_service.is_token_valid.return_value = False

        result = customer_service.find_customers_batch(["John", "Jane"])

        assert result == {"John": None, "Jane": None}

    @patch("src.utils.qbo_service.customers.ThreadPoolExecutor")
    def test_find_customers_batch_mixed_results(self, mock_executor_class, customer_service, sample_customer):
        """Test batch find with mixed results."""
        # Ensure cache is completely empty
        customer_service._customer_cache.clear()
        customer_service._cache_timestamp = None

        # Create a mock executor that runs tasks immediately
        mock_executor = Mock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Mock the futures
        future1 = Mock()
        future1.result.return_value = sample_customer
        future2 = Mock()
        future2.result.return_value = None

        # Track submissions and create future mapping
        submissions = []

        def mock_submit(func, lookup):
            submissions.append(lookup)
            if lookup == "John Doe":
                return future1
            else:
                return future2

        mock_executor.submit.side_effect = mock_submit

        # Mock as_completed to return futures in order
        with patch("src.utils.qbo_service.customers.as_completed") as mock_as_completed:
            mock_as_completed.return_value = [future1, future2]

            result = customer_service.find_customers_batch(["John Doe", "Jane Smith"])

        assert result["John Doe"] == sample_customer
        assert result["Jane Smith"] is None
        assert mock_executor.submit.call_count == 2

    @patch.object(QBOCustomerService, "find_customer")
    def test_find_customers_batch_with_duplicates(self, mock_find, customer_service, sample_customer):
        """Test batch find handles duplicates."""
        mock_find.return_value = sample_customer

        # Input has duplicates
        result = customer_service.find_customers_batch(["John Doe", "John Doe", "JOHN DOE"])

        # Should only search once for unique values
        assert mock_find.call_count == 2  # "John Doe" and "JOHN DOE" are different
        assert result["John Doe"] == sample_customer
        assert result["JOHN DOE"] == sample_customer

    def test_find_customers_batch_with_cache(self, customer_service, sample_customer):
        """Test batch find uses cache."""
        # Populate cache
        customer_service._customer_cache["john doe"] = sample_customer
        customer_service._cache_timestamp = datetime.now().timestamp()

        with patch.object(customer_service, "find_customer") as mock_find:
            mock_find.return_value = {"Id": "456", "DisplayName": "Jane Smith"}

            result = customer_service.find_customers_batch(["John Doe", "Jane Smith"])

        # Should only search for uncached customer
        mock_find.assert_called_once_with("Jane Smith")
        assert result["John Doe"] == sample_customer  # From cache
        assert result["Jane Smith"]["Id"] == "456"  # From API

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_create_customer_success(self, mock_request, customer_service):
        """Test successful customer creation."""
        customer_data = {
            "DisplayName": "New Customer",
            "GivenName": "New",
            "FamilyName": "Customer",
        }

        mock_request.return_value = {"Customer": {"Id": "789", **customer_data}}

        result = customer_service.create_customer(customer_data)

        assert result["Id"] == "789"
        assert result["DisplayName"] == "New Customer"
        mock_request.assert_called_once_with("POST", "customer", data=customer_data)

    def test_create_customer_not_authenticated(self, customer_service):
        """Test create customer when not authenticated."""
        customer_service.auth_service.is_token_valid.return_value = False

        result = customer_service.create_customer({"DisplayName": "Test"})

        assert result is None

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_update_customer_success(self, mock_request, customer_service):
        """Test successful customer update."""
        customer_data = {
            "Id": "123",
            "SyncToken": "1",
            "DisplayName": "Updated Customer",
        }

        mock_request.return_value = {"Customer": customer_data}

        result = customer_service.update_customer(customer_data)

        assert result == customer_data
        mock_request.assert_called_once_with("POST", "customer", data=customer_data)

    def test_get_customer_cache_stats_empty(self, customer_service):
        """Test cache stats when cache is empty."""
        stats = customer_service.get_customer_cache_stats()

        assert stats["cache_size"] == 0
        assert stats["cache_age_seconds"] == 0
        assert stats["cache_valid"] is False
        assert stats["cache_ttl"] == 300

    def test_get_customer_cache_stats_populated(self, customer_service):
        """Test cache stats when cache has data."""
        # Populate cache
        customer_service._customer_cache = {
            "john doe": {"Id": "1"},
            "jane smith": {"Id": "2"},
            "id_123": {"Id": "123"},  # ID entries not counted
        }
        customer_service._cache_timestamp = datetime.now().timestamp() - 60

        stats = customer_service.get_customer_cache_stats()

        assert stats["cache_size"] == 2  # Only non-ID entries
        assert 59 <= stats["cache_age_seconds"] <= 61
        assert stats["cache_valid"] is True

    def test_is_cache_valid_no_timestamp(self, customer_service):
        """Test cache validity with no timestamp."""
        assert customer_service._is_cache_valid() is False

    def test_is_cache_valid_expired(self, customer_service):
        """Test cache validity when expired."""
        customer_service._cache_timestamp = datetime.now().timestamp() - 400
        assert customer_service._is_cache_valid() is False

    def test_is_cache_valid_not_expired(self, customer_service):
        """Test cache validity when not expired."""
        customer_service._cache_timestamp = datetime.now().timestamp() - 100
        assert customer_service._is_cache_valid() is True

    def test_update_customer_cache(self, customer_service):
        """Test updating customer cache."""
        customers = [
            {"Id": "1", "DisplayName": "John Doe"},
            {"Id": "2", "DisplayName": "Jane Smith"},
        ]

        customer_service._update_customer_cache(customers)

        assert len(customer_service._customer_cache) == 4  # 2 by name, 2 by ID
        assert customer_service._customer_cache["john doe"]["Id"] == "1"
        assert customer_service._customer_cache["jane smith"]["Id"] == "2"
        assert customer_service._customer_cache["id_1"]["Id"] == "1"
        assert customer_service._customer_cache["id_2"]["Id"] == "2"
        assert customer_service._cache_timestamp is not None

    def test_get_cached_customer_by_name(self, customer_service, sample_customer):
        """Test getting cached customer by name."""
        customer_service._customer_cache["john doe"] = sample_customer
        customer_service._cache_timestamp = datetime.now().timestamp()

        result = customer_service.get_cached_customer("John Doe")
        assert result == sample_customer

    def test_get_cached_customer_by_id(self, customer_service, sample_customer):
        """Test getting cached customer by ID."""
        customer_service._customer_cache["id_123"] = sample_customer
        customer_service._cache_timestamp = datetime.now().timestamp()

        result = customer_service.get_cached_customer("123")
        assert result == sample_customer

    def test_get_cached_customer_not_found(self, customer_service):
        """Test getting non-existent cached customer."""
        customer_service._cache_timestamp = datetime.now().timestamp()

        result = customer_service.get_cached_customer("Nonexistent")
        assert result is None

    def test_clear_customer_cache(self, customer_service):
        """Test clearing customer cache."""
        # Populate cache
        customer_service._customer_cache = {"test": "data"}
        customer_service._cache_timestamp = datetime.now().timestamp()

        customer_service.clear_customer_cache()

        assert len(customer_service._customer_cache) == 0
        assert customer_service._cache_timestamp is None

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_get_all_customers_success(self, mock_request, customer_service):
        """Test getting all customers with pagination."""
        # First page
        page1_customers = [{"Id": str(i), "DisplayName": f"Customer {i}"} for i in range(1000)]
        # Second page (partial)
        page2_customers = [{"Id": str(i), "DisplayName": f"Customer {i}"} for i in range(1000, 1200)]

        mock_request.side_effect = [
            {"QueryResponse": {"Customer": page1_customers}},
            {"QueryResponse": {"Customer": page2_customers}},
        ]

        result = customer_service.get_all_customers(use_cache=False)

        assert len(result) == 1200
        assert result[0]["DisplayName"] == "Customer 0"  # Should be sorted
        assert mock_request.call_count == 2

        # Check cache was updated
        assert customer_service._cache_timestamp is not None

    @patch.object(QBOCustomerService, "_make_qbo_request")
    def test_get_all_customers_no_results(self, mock_request, customer_service):
        """Test getting all customers when none exist."""
        mock_request.return_value = {"QueryResponse": {}}

        result = customer_service.get_all_customers()

        assert result == []

    def test_get_all_customers_from_cache(self, customer_service):
        """Test getting all customers from cache."""
        # Populate cache
        customers = [
            {"Id": "1", "DisplayName": "B Customer"},
            {"Id": "2", "DisplayName": "A Customer"},
        ]
        customer_service._update_customer_cache(customers)

        with patch.object(customer_service, "_make_qbo_request") as mock_request:
            result = customer_service.get_all_customers(use_cache=True)

        # Should not make API request
        mock_request.assert_not_called()
        assert len(result) == 2
        # get_all_customers extracts non-ID entries from cache but doesn't sort them
        # The sorting happens when fetching from API
        assert any(c["DisplayName"] == "A Customer" for c in result)
        assert any(c["DisplayName"] == "B Customer" for c in result)

    def test_get_all_customers_not_authenticated(self, customer_service):
        """Test getting all customers when not authenticated."""
        customer_service.auth_service.is_token_valid.return_value = False

        result = customer_service.get_all_customers()

        assert result == []

    def test_escape_query_value_inheritance(self, customer_service):
        """Test that escape_query_value is inherited from base class."""
        # Should have access to parent's escape method
        assert hasattr(customer_service, "_escape_query_value")
        # The method escapes single quotes and then URL encodes
        assert customer_service._escape_query_value("O'Brien") == "O%5C%27Brien"
