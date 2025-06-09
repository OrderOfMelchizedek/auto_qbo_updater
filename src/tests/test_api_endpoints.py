"""Tests for API endpoints."""
import json
from io import BytesIO
from unittest.mock import patch

import pytest
from werkzeug.datastructures import FileStorage

from src.app import app


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
    @patch("src.app.QuickBooksClient")
    def test_create_customer_success(self, MockQuickBooksClient, client):
        """Test successful customer creation."""
        mock_qb_client_instance = MockQuickBooksClient.return_value
        mock_created_customer = {"Id": "1", "DisplayName": "Test Customer"}
        mock_qb_client_instance.create_customer.return_value = mock_created_customer

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
        MockQuickBooksClient.assert_called_once_with(session_id="test-session-id")
        mock_qb_client_instance.create_customer.assert_called_once_with(
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
        response = client.post("/api/customers", headers=headers) # No json data
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data["success"] is False
        assert "Missing JSON request body" in data["error"]

    @patch("src.app.QuickBooksClient")
    def test_create_customer_quickbooks_error(self, MockQuickBooksClient, client):
        """Test customer creation when QuickBooksClient raises QuickBooksError."""
        mock_qb_client_instance = MockQuickBooksClient.return_value
        # Import QuickBooksError from the correct module for the test
        from src.quickbooks_service import QuickBooksError
        mock_qb_client_instance.create_customer.side_effect = QuickBooksError(
            "QuickBooks API Error", details={"code": "1000", "message": "API limit reached"}
        )

        customer_data = {"DisplayName": "Test Customer"}
        headers = {"X-Session-ID": "test-session-id"}

        response = client.post("/api/customers", json=customer_data, headers=headers)
        data = json.loads(response.data)

        assert response.status_code == 500
        assert data["success"] is False
        assert "QuickBooks API Error" in data["error"]
        assert data["details"]["code"] == "1000"
        MockQuickBooksClient.assert_called_once_with(session_id="test-session-id")

    @patch("src.app.QuickBooksClient")
    def test_create_customer_general_exception(self, MockQuickBooksClient, client):
        """Test customer creation when a general exception occurs."""
        mock_qb_client_instance = MockQuickBooksClient.return_value
        mock_qb_client_instance.create_customer.side_effect = Exception("Something went wrong")

        customer_data = {"DisplayName": "Test Customer"}
        headers = {"X-Session-ID": "test-session-id"}

        response = client.post("/api/customers", json=customer_data, headers=headers)
        data = json.loads(response.data)

        assert response.status_code == 500
        assert data["success"] is False
        assert "Failed to create customer" in data["error"]
        MockQuickBooksClient.assert_called_once_with(session_id="test-session-id")
