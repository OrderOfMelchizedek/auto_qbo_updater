"""
Unit tests for QBO Sales Receipt Service module.
"""

import json
from unittest.mock import Mock, patch

import pytest

from src.utils.exceptions import QBOAPIException
from src.utils.qbo_service.sales_receipts import QBOSalesReceiptService


class TestQBOSalesReceiptService:
    """Test the QBO sales receipt service functionality."""

    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service."""
        mock = Mock()
        mock.is_token_valid.return_value = True
        mock.api_base = "https://sandbox-quickbooks.api.intuit.com/v3/company/"
        mock.realm_id = "test_realm_123"
        return mock

    @pytest.fixture
    def sales_receipt_service(self, mock_auth_service):
        """Create a sales receipt service instance."""
        return QBOSalesReceiptService(mock_auth_service)

    @pytest.fixture
    def sample_sales_receipt(self):
        """Create a sample sales receipt."""
        return {
            "Id": "SR123",
            "DocNumber": "1001",
            "TxnDate": "2024-01-15",
            "CustomerRef": {"value": "123", "name": "John Doe"},
            "Line": [
                {
                    "DetailType": "SalesItemLineDetail",
                    "Amount": 100.00,
                    "SalesItemLineDetail": {"ItemRef": {"value": "1", "name": "Donation"}},
                }
            ],
            "TotalAmt": 100.00,
            "PaymentRefNum": "CHK1234",
        }

    def test_find_sales_receipt_not_authenticated(self, sales_receipt_service):
        """Test find sales receipt when not authenticated."""
        sales_receipt_service.auth_service.is_token_valid.return_value = False

        result = sales_receipt_service.find_sales_receipt("1234", "2024-01-15", "123")

        assert result is None

    @patch.object(QBOSalesReceiptService, "_make_qbo_request")
    def test_find_sales_receipt_found(self, mock_request, sales_receipt_service, sample_sales_receipt):
        """Test finding an existing sales receipt."""
        mock_request.return_value = {"QueryResponse": {"SalesReceipt": [sample_sales_receipt]}}

        result = sales_receipt_service.find_sales_receipt("CHK1234", "2024-01-15", "123")

        assert result == sample_sales_receipt
        # Verify the query (URL encoded)
        call_args = mock_request.call_args[0]
        assert "query?query=" in call_args[1]
        assert "PaymentRefNum" in call_args[1]
        assert "TxnDate" in call_args[1]
        assert "CustomerRef" in call_args[1]

    @patch.object(QBOSalesReceiptService, "_make_qbo_request")
    def test_find_sales_receipt_not_found(self, mock_request, sales_receipt_service):
        """Test finding sales receipt that doesn't exist."""
        mock_request.return_value = {"QueryResponse": {}}

        result = sales_receipt_service.find_sales_receipt("CHK9999", "2024-01-15", "123")

        assert result is None

    @patch.object(QBOSalesReceiptService, "_make_qbo_request")
    def test_find_sales_receipt_multiple_found(self, mock_request, sales_receipt_service, sample_sales_receipt):
        """Test finding sales receipt returns first when multiple found."""
        receipt2 = sample_sales_receipt.copy()
        receipt2["Id"] = "SR124"

        mock_request.return_value = {"QueryResponse": {"SalesReceipt": [sample_sales_receipt, receipt2]}}

        result = sales_receipt_service.find_sales_receipt("CHK1234", "2024-01-15", "123")

        assert result == sample_sales_receipt  # Returns first one

    def test_create_sales_receipt_not_authenticated(self, sales_receipt_service):
        """Test create sales receipt when not authenticated."""
        sales_receipt_service.auth_service.is_token_valid.return_value = False

        result = sales_receipt_service.create_sales_receipt({"test": "data"})

        assert result["error"] is True
        assert "Not authenticated" in result["message"]

    @patch.object(QBOSalesReceiptService, "_make_qbo_request")
    def test_create_sales_receipt_success(self, mock_request, sales_receipt_service, sample_sales_receipt):
        """Test successful sales receipt creation."""
        mock_request.return_value = {"SalesReceipt": sample_sales_receipt}

        receipt_data = {
            "CustomerRef": {"value": "123"},
            "TxnDate": "2024-01-15",
            "Line": [{"Amount": 100.00}],
        }

        result = sales_receipt_service.create_sales_receipt(receipt_data)

        assert result == sample_sales_receipt
        mock_request.assert_called_once_with("POST", "salesreceipt", data=receipt_data)

    @patch.object(QBOSalesReceiptService, "_make_qbo_request")
    def test_create_sales_receipt_api_error(self, mock_request, sales_receipt_service):
        """Test sales receipt creation with API error."""
        error_response = json.dumps(
            {
                "Fault": {
                    "Error": [
                        {
                            "Message": "Invalid Reference Id",
                            "Detail": "Invalid Reference Id : Accounts element id 5 is invalid",
                            "code": "2500",
                        }
                    ]
                }
            }
        )

        mock_request.side_effect = QBOAPIException(
            "Invalid account reference", status_code=400, response_text=error_response, user_message="Bad request"
        )

        result = sales_receipt_service.create_sales_receipt({"test": "data"})

        assert result["error"] is True
        assert result["setupType"] == "account"
        assert result["invalidId"] == "5"
        assert result["requiresSetup"] is True

    @patch.object(QBOSalesReceiptService, "_make_qbo_request")
    def test_create_sales_receipt_item_error(self, mock_request, sales_receipt_service):
        """Test sales receipt creation with invalid item reference."""
        error_response = json.dumps(
            {
                "Fault": {
                    "Error": [
                        {
                            "Message": "Invalid Reference Id",
                            "Detail": "Invalid Reference Id : Item elements id 10 is invalid",
                            "code": "2500",
                        }
                    ]
                }
            }
        )

        mock_request.side_effect = QBOAPIException(
            "Invalid item reference", status_code=400, response_text=error_response
        )

        result = sales_receipt_service.create_sales_receipt({"test": "data"})

        assert result["error"] is True
        assert result["setupType"] == "item"
        assert result["invalidId"] == "10"
        assert result["requiresSetup"] is True

    @patch.object(QBOSalesReceiptService, "_make_qbo_request")
    def test_create_sales_receipt_payment_method_error(self, mock_request, sales_receipt_service):
        """Test sales receipt creation with invalid payment method."""
        error_response = json.dumps(
            {
                "Fault": {
                    "Error": [
                        {
                            "Message": "Invalid Reference Id",
                            "Detail": "Invalid Reference Id : PaymentMethod id CHECK is invalid",
                            "code": "2500",
                        }
                    ]
                }
            }
        )

        mock_request.side_effect = QBOAPIException(
            "Invalid payment method", status_code=400, response_text=error_response
        )

        result = sales_receipt_service.create_sales_receipt({"test": "data"})

        assert result["error"] is True
        assert result["setupType"] == "paymentMethod"
        assert result["invalidId"] == "CHECK"
        assert result["requiresSetup"] is True

    @patch.object(QBOSalesReceiptService, "_make_qbo_request")
    def test_create_sales_receipt_validation_error(self, mock_request, sales_receipt_service):
        """Test sales receipt creation with validation error."""
        error_response = json.dumps(
            {
                "Fault": {
                    "Error": [
                        {
                            "Message": "Object is not valid",
                            "Detail": "Object validation failed\nRequired field missing: TxnDate\nAmount must be positive",
                            "code": "6000",
                        }
                    ]
                }
            }
        )

        mock_request.side_effect = QBOAPIException("Validation error", status_code=400, response_text=error_response)

        result = sales_receipt_service.create_sales_receipt({"test": "data"})

        assert result["error"] is True
        assert result["validationError"] is True
        # The validation details parsing may vary, so just check that we got some details
        assert len(result["validationDetails"]) >= 1
        assert any("TxnDate" in detail for detail in result["validationDetails"])

    @patch.object(QBOSalesReceiptService, "_make_qbo_request")
    def test_create_sales_receipt_duplicate_error(self, mock_request, sales_receipt_service):
        """Test sales receipt creation with duplicate document number."""
        error_response = json.dumps(
            {
                "Fault": {
                    "Error": [
                        {
                            "Message": "Duplicate Document Number",
                            "Detail": "Duplicate Document Number : DocNumber 1001 is already in use",
                            "code": "6140",
                        }
                    ]
                }
            }
        )

        mock_request.side_effect = QBOAPIException("Duplicate error", status_code=400, response_text=error_response)

        result = sales_receipt_service.create_sales_receipt({"test": "data"})

        assert result["error"] is True
        assert result["duplicateError"] is True
        assert result["duplicateField"] == "DocNumber"

    @patch.object(QBOSalesReceiptService, "_make_qbo_request")
    def test_create_sales_receipt_generic_error(self, mock_request, sales_receipt_service):
        """Test sales receipt creation with generic error."""
        mock_request.side_effect = Exception("Network timeout")

        result = sales_receipt_service.create_sales_receipt({"test": "data"})

        assert result["error"] is True
        assert result["message"] == "Network timeout"

    def test_parse_qbo_error_no_fault(self, sales_receipt_service):
        """Test parsing error with no Fault structure."""
        error_json = {"message": "Simple error"}

        result = sales_receipt_service._parse_qbo_error(error_json)

        assert result == {}

    def test_parse_qbo_error_empty_errors(self, sales_receipt_service):
        """Test parsing error with empty errors list."""
        error_json = {"Fault": {"Error": []}}

        result = sales_receipt_service._parse_qbo_error(error_json)

        assert result == {}

    def test_parse_qbo_error_dict_format(self, sales_receipt_service):
        """Test parsing error when Error is dict instead of list."""
        error_json = {"Fault": {"Error": {"Message": "Test error", "Detail": "Test detail", "code": "1000"}}}

        result = sales_receipt_service._parse_qbo_error(error_json)

        assert result["message"] == "Test error"
        assert result["detail"] == "Test detail"
        assert result["code"] == "1000"

    def test_parse_qbo_error_account_variations(self, sales_receipt_service):
        """Test parsing different account error message formats."""
        # Test "Accounts element id" format
        error_json1 = {
            "Fault": {
                "Error": [
                    {
                        "Message": "Invalid Reference Id",
                        "Detail": "Invalid Reference Id : Accounts element id 123 is invalid",
                    }
                ]
            }
        }

        result1 = sales_receipt_service._parse_qbo_error(error_json1)
        assert result1["setupType"] == "account"
        assert result1["invalidId"] == "123"

        # Test "Account id" format
        error_json2 = {
            "Fault": {
                "Error": [
                    {"Message": "Invalid Reference Id", "Detail": "Invalid Reference Id : Account id 456 is invalid"}
                ]
            }
        }

        result2 = sales_receipt_service._parse_qbo_error(error_json2)
        assert result2["setupType"] == "account"
        assert result2["invalidId"] == "456"

    def test_parse_qbo_error_item_variations(self, sales_receipt_service):
        """Test parsing different item error message formats."""
        # Test variations in capitalization
        variations = ["Item elements id 99 is invalid", "Item elements Id 99 is invalid", "Item id 99 is invalid"]

        for detail in variations:
            error_json = {
                "Fault": {"Error": [{"Message": "Invalid Reference Id", "Detail": f"Invalid Reference Id : {detail}"}]}
            }

            result = sales_receipt_service._parse_qbo_error(error_json)
            assert result["setupType"] == "item"
            assert result["invalidId"] == "99"

    def test_escape_query_value_special_chars(self, sales_receipt_service):
        """Test escaping special characters in query values."""
        # Verify inheritance from base class
        assert hasattr(sales_receipt_service, "_escape_query_value")

        # Test escaping - the method escapes single quotes and URL encodes
        assert sales_receipt_service._escape_query_value("CHK'123") == "CHK%5C%27123"
        assert sales_receipt_service._escape_query_value("2024-01-15") == "2024-01-15"

    @patch.object(QBOSalesReceiptService, "_make_qbo_request")
    def test_find_sales_receipt_exception_handling(self, mock_request, sales_receipt_service):
        """Test exception handling in find_sales_receipt."""
        mock_request.side_effect = Exception("Unexpected error")

        result = sales_receipt_service.find_sales_receipt("CHK123", "2024-01-15", "123")

        assert result is None  # Should return None on exception

    def test_create_sales_receipt_invalid_json_response(self, sales_receipt_service):
        """Test handling invalid JSON in error response."""
        with patch.object(sales_receipt_service, "_make_qbo_request") as mock_request:
            mock_request.side_effect = QBOAPIException("Error", response_text="Not valid JSON")

            result = sales_receipt_service.create_sales_receipt({})

            assert result["error"] is True
            assert "detail" in result
