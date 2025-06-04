"""Unit tests for document endpoints."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    """Get authorization headers for testing."""
    from src.services.auth.jwt_handler import create_access_token

    token = create_access_token({"sub": "test_user", "role": "user"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_s3_service():
    """Mock S3 service for testing."""
    with patch("src.api.endpoints.documents.s3_service") as mock:
        yield mock


def test_prepare_upload_success(auth_headers, mock_s3_service):
    """Test preparing file upload with presigned URLs."""
    mock_s3_service.generate_presigned_upload_url.return_value = (
        "https://s3.example.com/upload"
    )

    request_data = {
        "file_names": ["donation1.jpg", "donation2.pdf"],
    }

    response = client.post(
        "/api/documents/upload/prepare",
        json=request_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["upload_urls"]) == 2
    assert "donation1.jpg" in data["data"]["upload_urls"]
    assert "donation2.pdf" in data["data"]["upload_urls"]


def test_prepare_upload_invalid_file_type(auth_headers):
    """Test upload preparation with invalid file type."""
    request_data = {
        "file_names": ["invalid.exe"],
    }

    response = client.post(
        "/api/documents/upload/prepare",
        json=request_data,
        headers=auth_headers,
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_prepare_upload_too_many_files(auth_headers):
    """Test upload preparation with too many files."""
    request_data = {
        "file_names": [f"file{i}.jpg" for i in range(25)],  # 25 files, max is 20
    }

    response = client.post(
        "/api/documents/upload/prepare",
        json=request_data,
        headers=auth_headers,
    )

    assert response.status_code == 422  # Validation error


@patch("src.api.endpoints.documents.s3_service")
def test_complete_upload_success(mock_s3, auth_headers):
    """Test completing file upload."""
    mock_s3.file_exists.return_value = True
    mock_s3.get_file_info.return_value = {"ContentLength": 1024}

    file_metadata = [
        {
            "file_id": "file_123",
            "filename": "donation1.jpg",
            "file_type": "jpg",
            "s3_key": "uploads/test_user/batch_123/file_123/donation1.jpg",
        }
    ]

    response = client.post(
        "/api/documents/upload/complete",
        json={"batch_id": "batch_123", "file_metadata": file_metadata},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["original_name"] == "donation1.jpg"


@patch("src.workers.tasks.document_tasks.check_extraction_status")
def test_get_processing_status(mock_check_status, auth_headers):
    """Test getting document processing status."""
    # Mock the Celery task status check
    mock_check_status.return_value = {
        "task_id": "task_123",
        "status": "STARTED",
        "ready": False,
        "successful": None,
        "result": {"batch_id": "batch_123"},
    }

    response = client.get(
        "/api/documents/processing/task_123",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["task_id"] == "task_123"
    assert data["data"]["status"] == "processing"


def test_direct_upload_requires_auth():
    """Test that direct upload requires authentication."""
    response = client.post("/api/documents/upload/direct")

    assert response.status_code == 401
