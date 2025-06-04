"""Unit tests for S3 storage service."""
import io
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from src.services.storage.s3_service import S3Service, S3StorageError


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    with patch("src.services.storage.s3_service.boto3.client") as mock_client:
        yield mock_client.return_value


def test_s3_service_initialization(mock_s3_client):
    """Test S3Service initialization."""
    with patch("src.services.storage.s3_service.settings") as mock_settings:
        mock_settings.AWS_S3_BUCKET_NAME = "test-bucket"
        mock_settings.AWS_ACCESS_KEY_ID = "test-key-id"
        mock_settings.AWS_SECRET_ACCESS_KEY = "test-secret"
        mock_settings.AWS_S3_REGION = "us-east-1"

        service = S3Service()
        assert service.bucket_name == "test-bucket"
        assert service.client is not None


def test_upload_file_success(mock_s3_client):
    """Test successful file upload to S3."""
    service = S3Service()
    file_content = b"test content"
    file_object = io.BytesIO(file_content)
    key = "documents/test.pdf"

    result = service.upload_file(file_object, key)

    assert result == key
    mock_s3_client.put_object.assert_called_once()


def test_upload_file_failure(mock_s3_client):
    """Test file upload failure handling."""
    service = S3Service()
    mock_s3_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchBucket"}}, "PutObject"
    )

    with pytest.raises(S3StorageError) as exc_info:
        service.upload_file(io.BytesIO(b"test"), "test.pdf")

    assert "Failed to upload file" in str(exc_info.value)


def test_download_file_success(mock_s3_client):
    """Test successful file download from S3."""
    service = S3Service()
    mock_response = {"Body": io.BytesIO(b"test content")}
    mock_s3_client.get_object.return_value = mock_response

    content = service.download_file("documents/test.pdf")

    assert content == b"test content"
    mock_s3_client.get_object.assert_called_once()


def test_download_file_not_found(mock_s3_client):
    """Test download of non-existent file."""
    service = S3Service()
    mock_s3_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey"}}, "GetObject"
    )

    with pytest.raises(S3StorageError) as exc_info:
        service.download_file("nonexistent.pdf")

    assert "File not found" in str(exc_info.value)


def test_delete_file_success(mock_s3_client):
    """Test successful file deletion from S3."""
    service = S3Service()

    result = service.delete_file("documents/test.pdf")

    assert result is True
    mock_s3_client.delete_object.assert_called_once()


def test_generate_presigned_url(mock_s3_client):
    """Test presigned URL generation."""
    service = S3Service()
    mock_s3_client.generate_presigned_url.return_value = "https://s3.example.com/test"

    url = service.generate_presigned_url("documents/test.pdf", expiration=3600)

    assert url.startswith("https://")
    mock_s3_client.generate_presigned_url.assert_called_once()
