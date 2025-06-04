"""Tests for batch document upload endpoint."""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authorization headers for testing."""
    from src.services.auth.jwt_handler import create_access_token

    token = create_access_token({"sub": "test-user-id", "email": "test@example.com"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_s3_service():
    """Mock S3 service."""
    with patch("src.api.endpoints.documents.s3_service") as mock:
        mock.upload_file = MagicMock()
        mock.file_exists = MagicMock(return_value=True)
        mock.get_file_info = MagicMock(return_value={"ContentLength": 1000})
        yield mock


class TestBatchUpload:
    """Test batch file upload functionality."""

    def test_upload_batch_success(self, auth_headers, mock_s3_service):
        """Test successful batch upload of multiple files."""
        # Create test files
        files = [
            ("files", ("test1.jpg", b"test content 1", "image/jpeg")),
            ("files", ("test2.png", b"test content 2", "image/png")),
            ("files", ("test3.pdf", b"test content 3", "application/pdf")),
        ]

        response = client.post(
            "/api/documents/upload/batch",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 3
        assert data["message"] == "Uploaded 3 files successfully"

        # Verify each file
        for i, file_data in enumerate(data["data"]):
            assert file_data["original_name"] == f"test{i+1}.{['jpg', 'png', 'pdf'][i]}"
            assert file_data["file_type"] in ["jpg", "jpeg", "png", "pdf"]
            assert file_data["file_size"] == len(f"test content {i+1}")
            assert file_data["uploaded_by"] == "test-user-id"
            assert file_data["batch_id"] is not None

        # Verify S3 calls
        assert mock_s3_service.upload_file.call_count == 3

    def test_upload_batch_with_batch_id(self, auth_headers, mock_s3_service):
        """Test batch upload with provided batch ID."""
        batch_id = str(uuid.uuid4())
        files = [
            ("files", ("test1.jpg", b"test content", "image/jpeg")),
        ]

        response = client.post(
            f"/api/documents/upload/batch?batch_id={batch_id}",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"][0]["batch_id"] == batch_id

    def test_upload_batch_max_files(self, auth_headers, mock_s3_service):
        """Test batch upload with maximum allowed files (20)."""
        files = [
            ("files", (f"test{i}.jpg", b"content", "image/jpeg")) for i in range(20)
        ]

        response = client.post(
            "/api/documents/upload/batch",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 20

    def test_upload_batch_exceeds_max_files(self, auth_headers, mock_s3_service):
        """Test batch upload with too many files."""
        files = [
            ("files", (f"test{i}.jpg", b"content", "image/jpeg")) for i in range(21)
        ]

        response = client.post(
            "/api/documents/upload/batch",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Maximum 20 files allowed per batch" in data["detail"]

    def test_upload_batch_invalid_file_type(self, auth_headers, mock_s3_service):
        """Test batch upload with invalid file type."""
        files = [
            ("files", ("test.txt", b"test content", "text/plain")),
        ]

        response = client.post(
            "/api/documents/upload/batch",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Unsupported file type" in data["detail"]

    def test_upload_batch_file_too_large(self, auth_headers, mock_s3_service):
        """Test batch upload with file exceeding size limit."""
        # Create content larger than 20MB
        large_content = b"x" * (21 * 1024 * 1024)
        files = [
            ("files", ("test.jpg", large_content, "image/jpeg")),
        ]

        response = client.post(
            "/api/documents/upload/batch",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "File size exceeds maximum allowed" in data["detail"]

    def test_upload_batch_mixed_file_types(self, auth_headers, mock_s3_service):
        """Test batch upload with various supported file types."""
        files = [
            ("files", ("check.jpg", b"check image", "image/jpeg")),
            ("files", ("envelope.png", b"envelope image", "image/png")),
            ("files", ("statement.pdf", b"pdf content", "application/pdf")),
            ("files", ("donations.csv", b"csv content", "text/csv")),
        ]

        response = client.post(
            "/api/documents/upload/batch",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 4

        # Verify file types
        file_types = [f["file_type"] for f in data["data"]]
        assert "jpg" in file_types or "jpeg" in file_types
        assert "png" in file_types
        assert "pdf" in file_types
        assert "csv" in file_types

    def test_upload_batch_s3_failure(self, auth_headers, mock_s3_service):
        """Test batch upload when S3 upload fails."""
        mock_s3_service.upload_file.side_effect = Exception("S3 connection error")

        files = [
            ("files", ("test.jpg", b"test content", "image/jpeg")),
        ]

        response = client.post(
            "/api/documents/upload/batch",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to upload files" in data["detail"]

    def test_upload_batch_empty_filename(self, auth_headers, mock_s3_service):
        """Test batch upload with empty filename."""
        files = [
            ("files", ("", b"test content", "image/jpeg")),
        ]

        response = client.post(
            "/api/documents/upload/batch",
            files=files,
            headers=auth_headers,
        )

        # FastAPI returns 422 for validation errors when filename is empty
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
