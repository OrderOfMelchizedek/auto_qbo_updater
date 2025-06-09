"""Tests for API endpoints."""
import json
from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from werkzeug.datastructures import FileStorage

from src.app import app
from src.quickbooks_utils import QuickBooksError  # Import QuickBooksError


class TestAPIEndpoints:
    """Test API endpoints."""

    @pytest.fixture
    def client(self):
        """Create Flask test client."""
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["name"] == "QuickBooks Donation Manager API"
        assert "endpoints" in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "storage" in data
        assert "session" in data

    @patch("src.app.storage_backend")
    @patch("src.app.session_backend")
    def test_upload_success(self, mock_session, mock_storage, client):
        """Test successful file upload."""
        # Mock storage and session
        mock_storage.upload.return_value = "uploads/test_file.jpg"
        mock_session.store_upload_metadata.return_value = True

        # Create test file
        file_data = BytesIO(b"test file content")
        file = FileStorage(
            stream=file_data, filename="test_file.jpg", content_type="image/jpeg"
        )

        response = client.post(
            "/api/upload", data={"files": [file]}, content_type="multipart/form-data"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "upload_id" in data["data"]
        assert len(data["data"]["files"]) == 1

    def test_upload_no_files(self, client):
        """Test upload with no files."""
        response = client.post(
            "/api/upload", data={}, content_type="multipart/form-data"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "No files" in data["error"]

    def test_upload_invalid_file_type(self, client):
        """Test upload with invalid file type."""
        file_data = BytesIO(b"test file content")
        file = FileStorage(
            stream=file_data, filename="test_file.txt", content_type="text/plain"
        )

        response = client.post(
            "/api/upload", data={"files": [file]}, content_type="multipart/form-data"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Invalid file type" in data["error"]

    @patch("src.app.storage_backend")
    @patch("src.app.session_backend")
    @patch("src.app.process_donation_documents")
    def test_process_success(self, mock_process, mock_session, mock_storage, client):
        """Test successful document processing."""
        # Mock session metadata
        mock_session.get_upload_metadata.return_value = {
            "upload_id": "test_123",
            "files": ["file1.jpg"],
            "status": "uploaded",
        }

        # Mock storage
        mock_storage.get_file_paths.return_value = ["/path/to/file1.jpg"]

        # Mock processing
        mock_donations = [{"PaymentInfo": {"Payment_Ref": "1234", "Amount": 100.00}}]
        mock_metadata = {"raw_count": 1, "valid_count": 1, "duplicate_count": 0}
        mock_process.return_value = (mock_donations, mock_metadata)

        # Mock session update
        mock_session.update_upload_metadata.return_value = True

        response = client.post("/api/process", json={"upload_id": "test_123"})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert len(data["data"]["donations"]) == 1
        assert data["data"]["metadata"]["valid_count"] == 1

    def test_process_no_upload_id(self, client):
        """Test process without upload_id."""
        response = client.post("/api/process", json={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "upload_id is required" in data["error"]

    @patch("src.app.session_backend")
    def test_process_upload_not_found(self, mock_session, client):
        """Test process with non-existent upload_id."""
        mock_session.get_upload_metadata.return_value = None

        response = client.post("/api/process", json={"upload_id": "nonexistent"})

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Upload not found" in data["error"]

    # Tests for /api/customers endpoint
    @patch("src.app.create_customer_data_source")
    def test_create_customer_success(self, mock_create_data_source, client):
        """Test successful customer creation."""
        mock_data_source = Mock()
        mock_create_data_source.return_value = mock_data_source
        mock_created_customer = {"Id": "1", "DisplayName": "Test Customer"}
        mock_data_source.create_customer.return_value = mock_created_customer

        customer_data = {
            "DisplayName": "Test Customer",
            "GivenName": "Test",
            "FamilyName": "Customer",
            "PrimaryEmailAddr": "test@example.com",
        }
        headers = {"X-Session-ID": "test-session-id"}

        response = client.post("/api/customers", json=customer_data, headers=headers)
        data = json.loads(response.data)

        assert response.status_code == 200
        assert data["success"] is True
        assert data["data"] == mock_created_customer
        mock_create_data_source.assert_called_once_with(session_id="test-session-id")
        mock_data_source.create_customer.assert_called_once_with(
            customer_data=customer_data
        )

    def test_create_customer_missing_session_id(self, client):
        """Test customer creation with missing X-Session-ID."""
        customer_data = {"DisplayName": "Test Customer"}
        response = client.post("/api/customers", json=customer_data)
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data["success"] is False
        assert "Missing X-Session-ID header" in data["error"]

    def test_create_customer_missing_request_body(self, client):
        """Test customer creation with missing request body."""
        headers = {"X-Session-ID": "test-session-id"}
        response = client.post("/api/customers", headers=headers)  # No json data
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data["success"] is False
        assert "Missing JSON request body" in data["error"]

    @patch("src.app.create_customer_data_source")
    def test_create_customer_quickbooks_error(self, mock_create_data_source, client):
        """Test customer creation when QuickBooksClient raises QuickBooksError."""
        mock_data_source = Mock()
        mock_create_data_source.return_value = mock_data_source
        # Import QuickBooksError from the correct module for the test
        from src.quickbooks_utils import QuickBooksError

        mock_data_source.create_customer.side_effect = QuickBooksError(
            "QuickBooks API Error",
            status_code=500,
            detail={"code": "1000", "message": "API limit reached"},
        )

        customer_data = {"DisplayName": "Test Customer"}
        headers = {"X-Session-ID": "test-session-id"}

        response = client.post("/api/customers", json=customer_data, headers=headers)
        data = json.loads(response.data)

        assert response.status_code == 500
        assert data["success"] is False
        assert "QuickBooks API Error" in data["error"]
        assert data["details"]["code"] == "1000"
        mock_create_data_source.assert_called_once_with(session_id="test-session-id")

    @patch("src.app.create_customer_data_source")
    def test_create_customer_general_exception(self, mock_create_data_source, client):
        """Test customer creation when a general exception occurs."""
        mock_data_source = Mock()
        mock_create_data_source.return_value = mock_data_source
        mock_data_source.create_customer.side_effect = Exception("Something went wrong")

        customer_data = {"DisplayName": "Test Customer"}
        headers = {"X-Session-ID": "test-session-id"}

        response = client.post("/api/customers", json=customer_data, headers=headers)
        data = json.loads(response.data)

        assert response.status_code == 500
        assert data["success"] is False
        assert "Failed to create customer" in data["error"]
        mock_create_data_source.assert_called_once_with(session_id="test-session-id")

    # Tests for /api/search_customers
    @patch("src.app.CustomerMatcher")
    def test_search_customers_success(self, MockCustomerMatcher, client):
        """Test successful customer search."""
        mock_matcher_instance = MockCustomerMatcher.return_value
        mock_customers = [{"Id": "1", "DisplayName": "Test Customer"}]
        mock_matcher_instance.data_source.search_customer.return_value = mock_customers

        response = client.get(
            "/api/search_customers?search_term=Test",
            headers={"X-Session-ID": "test_session_id"},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert data["data"] == mock_customers
        mock_matcher_instance.data_source.search_customer.assert_called_once_with(
            "Test"
        )

    @patch("src.app.CustomerMatcher")
    def test_search_customers_quickbooks_error(self, MockCustomerMatcher, client):
        """Test customer search when QuickBooksError is raised."""
        mock_matcher_instance = MockCustomerMatcher.return_value
        mock_matcher_instance.data_source.search_customer.side_effect = QuickBooksError(
            "QB API Error", 500, {"detail": "Some QB detail"}
        )

        response = client.get(
            "/api/search_customers?search_term=ErrorCase",
            headers={"X-Session-ID": "test_session_id"},
        )

        assert response.status_code == 500  # As defined in app.py for QuickBooksError
        data = json.loads(response.data)
        assert data["success"] is False
        assert "QB API Error" in data["error"]
        assert data["details"] == {"detail": "Some QB detail"}

    def test_search_customers_missing_search_term(self, client):
        """Test customer search with missing search_term."""
        response = client.get(
            "/api/search_customers", headers={"X-Session-ID": "test_session_id"}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Missing search_term" in data["error"]

    def test_search_customers_missing_session_id(self, client):
        """Test customer search with missing X-Session-ID."""
        response = client.get("/api/search_customers?search_term=Test")
        assert response.status_code == 400  # As defined in app.py
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Missing X-Session-ID header" in data["error"]

    # Tests for /api/manual_match
    @patch("src.app.CustomerMatcher")
    def test_manual_match_success(self, MockCustomerMatcher, client):
        """Test successful manual match."""
        mock_matcher_instance = MockCustomerMatcher.return_value
        mock_qb_customer_detail = {"Id": "1", "DisplayName": "QB Customer"}
        mock_formatted_customer = {"DisplayName": "Formatted QB Customer", "Id": "1"}
        mock_merged_data = {
            "customer_ref": {"display_name": "Matched Customer", "id": "1"},
            "qb_address": {"line1": "123 Main St"},
            "qb_email": "test@example.com",
            "qb_phone": "123-456-7890",
            "updates_needed": True,
        }

        mock_matcher_instance.data_source.get_customer.return_value = (
            mock_qb_customer_detail
        )
        mock_matcher_instance.data_source.format_customer_data.return_value = (
            mock_formatted_customer
        )
        mock_matcher_instance.merge_customer_data.return_value = mock_merged_data

        sample_donation = {
            "payer_info": {"name": "Original Donor"},
            "payment_info": {"amount": 100},
            "status": {"matched": False},
        }
        request_payload = {
            "donation": sample_donation,
            "qb_customer_id": "1",
        }

        response = client.post(
            "/api/manual_match",
            json=request_payload,
            headers={"X-Session-ID": "test_session_id"},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

        updated_donation = data["data"]
        assert (
            updated_donation["payer_info"]["customer_ref"]
            == mock_merged_data["customer_ref"]
        )
        assert (
            updated_donation["payer_info"]["qb_address"]
            == mock_merged_data["qb_address"]
        )
        assert updated_donation["status"]["matched"] is True
        assert (
            updated_donation["status"]["edited"] is True
        )  # Because updates_needed was true

        mock_matcher_instance.data_source.get_customer.assert_called_once_with("1")
        # The input to format_customer_data is the output of get_customer
        mock_matcher_instance.data_source.format_customer_data.assert_called_once_with(
            mock_qb_customer_detail
        )
        # The input to merge_customer_data needs to be checked
        # carefully based on app.py logic
        expected_original_payer_contact_info = {
            "PayerInfo": sample_donation.get("payer_info", {}),
            "ContactInfo": sample_donation.get(
                "contact_info", {}
            ),  # Will be {} in this test case
        }
        mock_matcher_instance.merge_customer_data.assert_called_once_with(
            expected_original_payer_contact_info, mock_formatted_customer
        )

    @patch("src.app.CustomerMatcher")
    def test_manual_match_get_customer_raises_quickbooks_error(
        self, MockCustomerMatcher, client
    ):
        """Test manual match when get_customer raises QuickBooksError."""
        mock_matcher_instance = MockCustomerMatcher.return_value
        mock_matcher_instance.data_source.get_customer.side_effect = QuickBooksError(
            "Customer not found", 404, {"detail": "ID invalid"}
        )

        request_payload = {
            "donation": {"payer_info": {}, "payment_info": {}, "status": {}},
            "qb_customer_id": "nonexistent_id",
        }
        response = client.post(
            "/api/manual_match",
            json=request_payload,
            headers={"X-Session-ID": "test_session_id"},
        )

        assert response.status_code == 404  # Or the code set by QuickBooksError
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Customer not found" in data["error"]

    def test_manual_match_invalid_payload(self, client):
        """Test manual match with invalid request payload."""
        # Missing qb_customer_id
        response_missing_id = client.post(
            "/api/manual_match",
            json={"donation": {}},  # qb_customer_id is missing
            headers={"X-Session-ID": "test_session_id"},
        )
        assert response_missing_id.status_code == 400
        data_missing_id = json.loads(response_missing_id.data)
        assert data_missing_id["success"] is False
        assert "Missing 'donation' or 'qb_customer_id'" in data_missing_id["error"]

        # Missing donation
        response_missing_donation = client.post(
            "/api/manual_match",
            json={"qb_customer_id": "1"},  # donation is missing
            headers={"X-Session-ID": "test_session_id"},
        )
        assert response_missing_donation.status_code == 400
        data_missing_donation = json.loads(response_missing_donation.data)
        assert data_missing_donation["success"] is False
        assert (
            "Missing 'donation' or 'qb_customer_id'" in data_missing_donation["error"]
        )

    def test_manual_match_missing_session_id(self, client):
        """Test manual match with missing X-Session-ID."""
        request_payload = {
            "donation": {"payer_info": {}, "payment_info": {}, "status": {}},
            "qb_customer_id": "1",
        }
        response = client.post("/api/manual_match", json=request_payload)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Missing X-Session-ID header" in data["error"]
