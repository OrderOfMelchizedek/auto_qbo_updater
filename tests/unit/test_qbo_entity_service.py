"""
Unit tests for QBO Entity Service module.
"""

from unittest.mock import Mock, patch

import pytest

from src.utils.qbo_service.entities import QBOEntityService


class TestQBOEntityService:
    """Test the QBO entity service functionality."""

    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service."""
        mock = Mock()
        mock.is_token_valid.return_value = True
        mock.api_base = "https://sandbox-quickbooks.api.intuit.com/v3/company/"
        mock.realm_id = "test_realm_123"
        return mock

    @pytest.fixture
    def entity_service(self, mock_auth_service):
        """Create an entity service instance."""
        return QBOEntityService(mock_auth_service)

    @pytest.fixture
    def sample_account(self):
        """Create a sample account."""
        return {
            "Id": "1",
            "Name": "Donation Income",
            "FullyQualifiedName": "Income:Donation Income",
            "AccountType": "Income",
            "AccountSubType": "OtherPrimaryIncome",
            "Active": True,
            "CurrentBalance": 0,
        }

    @pytest.fixture
    def sample_item(self):
        """Create a sample item."""
        return {
            "Id": "1",
            "Name": "Donation",
            "Type": "Service",
            "Active": True,
            "IncomeAccountRef": {"value": "1", "name": "Donation Income"},
            "Description": "Tax-deductible donation",
        }

    @pytest.fixture
    def sample_payment_method(self):
        """Create a sample payment method."""
        return {
            "Id": "1",
            "Name": "Check",
            "Active": True,
            "Type": "NON_CREDIT_CARD",
        }

    # Account Tests
    def test_create_account_not_authenticated(self, entity_service):
        """Test create account when not authenticated."""
        entity_service.auth_service.is_token_valid.return_value = False

        result = entity_service.create_account({"Name": "Test", "AccountType": "Income"})

        assert result is None

    def test_create_account_missing_required_fields(self, entity_service):
        """Test create account with missing required fields."""
        # Missing AccountType
        result = entity_service.create_account({"Name": "Test Account"})
        assert result is None

        # Missing Name
        result = entity_service.create_account({"AccountType": "Income"})
        assert result is None

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_create_account_success(self, mock_request, entity_service, sample_account):
        """Test successful account creation."""
        mock_request.return_value = {"Account": sample_account}

        account_data = {
            "Name": "Donation Income",
            "AccountType": "Income",
            "AccountSubType": "OtherPrimaryIncome",
        }

        result = entity_service.create_account(account_data)

        assert result == sample_account
        mock_request.assert_called_once_with("POST", "account", data=account_data)

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_create_account_exception(self, mock_request, entity_service):
        """Test account creation with exception."""
        mock_request.side_effect = Exception("API Error")

        result = entity_service.create_account({"Name": "Test", "AccountType": "Income"})

        assert result is None

    # Item Tests
    def test_create_item_not_authenticated(self, entity_service):
        """Test create item when not authenticated."""
        entity_service.auth_service.is_token_valid.return_value = False

        result = entity_service.create_item({"Name": "Test Item"})

        assert result is None

    def test_create_item_missing_name(self, entity_service):
        """Test create item with missing name."""
        result = entity_service.create_item({})
        assert result is None

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_create_item_default_type(self, mock_request, entity_service, sample_item):
        """Test create item with default type."""
        mock_request.return_value = {"Item": sample_item}

        # No Type specified, should default to Service
        item_data = {"Name": "Donation"}

        result = entity_service.create_item(item_data)

        assert result == sample_item
        # Check that Type was added
        call_args = mock_request.call_args[1]
        assert call_args["data"]["Type"] == "Service"

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_create_item_inventory_type(self, mock_request, entity_service):
        """Test create item with Item type defaults to Non-inventory."""
        mock_request.return_value = {"Item": {"Id": "1", "Name": "Test"}}

        item_data = {"Name": "Test Item", "Type": "Item"}

        entity_service.create_item(item_data)

        # Check that ItemType was added
        call_args = mock_request.call_args[1]
        assert call_args["data"]["ItemType"] == "Non-inventory"

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_create_item_success(self, mock_request, entity_service, sample_item):
        """Test successful item creation."""
        mock_request.return_value = {"Item": sample_item}

        item_data = {
            "Name": "Donation",
            "Type": "Service",
            "IncomeAccountRef": {"value": "1"},
        }

        result = entity_service.create_item(item_data)

        assert result == sample_item
        mock_request.assert_called_once_with("POST", "item", data=item_data)

    # Payment Method Tests
    def test_create_payment_method_not_authenticated(self, entity_service):
        """Test create payment method when not authenticated."""
        entity_service.auth_service.is_token_valid.return_value = False

        result = entity_service.create_payment_method({"Name": "Test"})

        assert result is None

    def test_create_payment_method_missing_name(self, entity_service):
        """Test create payment method with missing name."""
        result = entity_service.create_payment_method({})
        assert result is None

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_create_payment_method_success(self, mock_request, entity_service, sample_payment_method):
        """Test successful payment method creation."""
        mock_request.return_value = {"PaymentMethod": sample_payment_method}

        pm_data = {"Name": "Check"}

        result = entity_service.create_payment_method(pm_data)

        assert result == sample_payment_method
        mock_request.assert_called_once_with("POST", "paymentmethod", data=pm_data)

    # Get All Items Tests
    def test_get_all_items_not_authenticated(self, entity_service):
        """Test get all items when not authenticated."""
        entity_service.auth_service.is_token_valid.return_value = False

        result = entity_service.get_all_items()

        assert result == []

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_get_all_items_single_page(self, mock_request, entity_service):
        """Test getting all items with single page of results."""
        items = [{"Id": str(i), "Name": f"Item {i}"} for i in range(10)]
        mock_request.return_value = {"QueryResponse": {"Item": items}}

        result = entity_service.get_all_items()

        assert len(result) == 10
        assert result[0]["Name"] == "Item 0"
        mock_request.assert_called_once()

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_get_all_items_pagination(self, mock_request, entity_service):
        """Test getting all items with pagination."""
        # First page - full 1000 items
        page1_items = [{"Id": str(i), "Name": f"Item {i}"} for i in range(1000)]
        # Second page - partial results
        page2_items = [{"Id": str(i), "Name": f"Item {i}"} for i in range(1000, 1250)]

        mock_request.side_effect = [
            {"QueryResponse": {"Item": page1_items}},
            {"QueryResponse": {"Item": page2_items}},
        ]

        result = entity_service.get_all_items()

        assert len(result) == 1250
        assert mock_request.call_count == 2

        # Verify pagination queries (URL encoded)
        first_call = mock_request.call_args_list[0][0][1]
        assert "query?query=" in first_call
        assert "STARTPOSITION" in first_call
        assert "1" in first_call

        second_call = mock_request.call_args_list[1][0][1]
        assert "query?query=" in second_call
        assert "STARTPOSITION" in second_call
        assert "1001" in second_call

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_get_all_items_no_results(self, mock_request, entity_service):
        """Test getting all items when none exist."""
        mock_request.return_value = {"QueryResponse": {}}

        result = entity_service.get_all_items()

        assert result == []

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_get_all_items_exception(self, mock_request, entity_service):
        """Test getting all items with exception."""
        mock_request.side_effect = Exception("API Error")

        result = entity_service.get_all_items()

        assert result == []

    # Get All Accounts Tests
    def test_get_all_accounts_not_authenticated(self, entity_service):
        """Test get all accounts when not authenticated."""
        entity_service.auth_service.is_token_valid.return_value = False

        result = entity_service.get_all_accounts()

        assert result == []

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_get_all_accounts_success(self, mock_request, entity_service):
        """Test getting all accounts successfully."""
        accounts = [
            {"Id": "1", "Name": "B Account"},
            {"Id": "2", "Name": "A Account"},
            {"Id": "3", "Name": "C Account"},
        ]
        mock_request.return_value = {"QueryResponse": {"Account": accounts}}

        result = entity_service.get_all_accounts()

        assert len(result) == 3
        # Should be sorted by name
        assert result[0]["Name"] == "A Account"
        assert result[1]["Name"] == "B Account"
        assert result[2]["Name"] == "C Account"

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_get_all_accounts_pagination(self, mock_request, entity_service):
        """Test getting all accounts with pagination."""
        # Create pages of accounts
        page1_accounts = [{"Id": str(i), "Name": f"Account {i:04d}"} for i in range(1000)]
        page2_accounts = [{"Id": str(i), "Name": f"Account {i:04d}"} for i in range(1000, 1100)]

        mock_request.side_effect = [
            {"QueryResponse": {"Account": page1_accounts}},
            {"QueryResponse": {"Account": page2_accounts}},
        ]

        result = entity_service.get_all_accounts()

        assert len(result) == 1100
        assert mock_request.call_count == 2
        # Should be sorted
        assert result[0]["Name"] == "Account 0000"
        assert result[-1]["Name"] == "Account 1099"

    # Get All Payment Methods Tests
    def test_get_all_payment_methods_not_authenticated(self, entity_service):
        """Test get all payment methods when not authenticated."""
        entity_service.auth_service.is_token_valid.return_value = False

        result = entity_service.get_all_payment_methods()

        assert result == []

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_get_all_payment_methods_success(self, mock_request, entity_service):
        """Test getting all payment methods successfully."""
        payment_methods = [
            {"Id": "1", "Name": "Cash"},
            {"Id": "2", "Name": "Check"},
            {"Id": "3", "Name": "ACH"},
        ]
        mock_request.return_value = {"QueryResponse": {"PaymentMethod": payment_methods}}

        result = entity_service.get_all_payment_methods()

        assert len(result) == 3
        # Should be sorted by name
        assert result[0]["Name"] == "ACH"
        assert result[1]["Name"] == "Cash"
        assert result[2]["Name"] == "Check"

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_get_all_payment_methods_empty_name(self, mock_request, entity_service):
        """Test sorting payment methods with empty names."""
        payment_methods = [
            {"Id": "1", "Name": "Check"},
            {"Id": "2", "Name": ""},  # Empty name
            {"Id": "3", "Name": "ACH"},
        ]
        mock_request.return_value = {"QueryResponse": {"PaymentMethod": payment_methods}}

        result = entity_service.get_all_payment_methods()

        assert len(result) == 3
        # Empty name should sort first
        assert result[0]["Name"] == ""
        assert result[1]["Name"] == "ACH"
        assert result[2]["Name"] == "Check"

    @patch.object(QBOEntityService, "_make_qbo_request")
    def test_get_all_payment_methods_case_insensitive_sort(self, mock_request, entity_service):
        """Test payment methods are sorted case-insensitively."""
        payment_methods = [
            {"Id": "1", "Name": "check"},
            {"Id": "2", "Name": "ACH"},
            {"Id": "3", "Name": "Cash"},
        ]
        mock_request.return_value = {"QueryResponse": {"PaymentMethod": payment_methods}}

        result = entity_service.get_all_payment_methods()

        # Should sort case-insensitively
        assert result[0]["Name"] == "ACH"
        assert result[1]["Name"] == "Cash"
        assert result[2]["Name"] == "check"

    def test_logging_in_create_methods(self, entity_service, caplog):
        """Test that successful creates are logged."""
        import logging

        caplog.set_level(logging.INFO)

        with patch.object(entity_service, "_make_qbo_request") as mock_request:
            # Test account creation logging
            mock_request.return_value = {"Account": {"Id": "123", "Name": "Test Account"}}
            entity_service.create_account({"Name": "Test Account", "AccountType": "Income"})
            assert "Successfully created account: Test Account (ID: 123)" in caplog.text

            # Test item creation logging
            caplog.clear()
            mock_request.return_value = {"Item": {"Id": "456", "Name": "Test Item"}}
            entity_service.create_item({"Name": "Test Item"})
            assert "Successfully created item: Test Item (ID: 456)" in caplog.text

            # Test payment method creation logging
            caplog.clear()
            mock_request.return_value = {"PaymentMethod": {"Id": "789", "Name": "Test PM"}}
            entity_service.create_payment_method({"Name": "Test PM"})
            assert "Successfully created payment method: Test PM (ID: 789)" in caplog.text

    def test_logging_in_get_all_methods(self, entity_service, caplog):
        """Test that batch retrieval is logged."""
        import logging

        caplog.set_level(logging.INFO)

        with patch.object(entity_service, "_make_qbo_request") as mock_request:
            # Test items logging
            items = [{"Id": str(i), "Name": f"Item {i}"} for i in range(5)]
            mock_request.return_value = {"QueryResponse": {"Item": items}}

            entity_service.get_all_items()

            assert "STARTING ITEM RETRIEVAL FROM QUICKBOOKS" in caplog.text
            assert "Retrieved 5 items" in caplog.text
            assert "Sample of retrieved items:" in caplog.text
            assert "1. Item 0" in caplog.text
