"""
Storage abstraction layer for file storage.

Supports local filesystem (development) and Amazon S3 (production).
"""
import logging
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, BinaryIO, Dict, List

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for file storage backends."""

    @abstractmethod
    def upload(self, file: BinaryIO, upload_id: str, filename: str) -> str:
        """
        Upload a file to storage.

        Args:
            file: File-like object to upload
            upload_id: Unique identifier for this upload batch
            filename: Name to store the file as

        Returns:
            str: Path or key where file was stored
        """
        pass

    @abstractmethod
    def list_files(self, upload_id: str) -> List[Dict[str, Any]]:
        """
        List all files for a given upload batch.

        Args:
            upload_id: Unique identifier for the upload batch

        Returns:
            List of file info dictionaries with 'filename' and 'path' keys
        """
        pass

    @abstractmethod
    def get_file_path(self, upload_id: str, filename: str) -> str:
        """
        Get the full path/URL for a specific file.

        Args:
            upload_id: Unique identifier for the upload batch
            filename: Name of the file

        Returns:
            str: Full path or URL to access the file
        """
        pass

    @abstractmethod
    def get_file_paths(self, upload_id: str) -> List[str]:
        """
        Get all file paths for a given upload batch.

        Args:
            upload_id: Unique identifier for the upload batch

        Returns:
            List of full paths/URLs for all files in the batch
        """
        pass

    @abstractmethod
    def delete_batch(self, upload_id: str) -> bool:
        """
        Delete all files in an upload batch.

        Args:
            upload_id: Unique identifier for the upload batch

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def file_exists(self, upload_id: str, filename: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            upload_id: Unique identifier for the upload batch
            filename: Name of the file

        Returns:
            bool: True if file exists, False otherwise
        """
        pass


class LocalStorage(StorageBackend):
    """Local filesystem storage for development."""

    def __init__(self, base_path: str = "uploads"):
        """
        Initialize local storage.

        Args:
            base_path: Base directory for storing uploads
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)

    def _get_batch_path(self, upload_id: str) -> Path:
        """Get the directory path for an upload batch."""
        return self.base_path / upload_id

    def upload(self, file: BinaryIO, upload_id: str, filename: str) -> str:
        """Upload file to local filesystem."""
        batch_path = self._get_batch_path(upload_id)
        batch_path.mkdir(exist_ok=True)

        file_path = batch_path / filename

        # Save the file
        with open(file_path, "wb") as f:
            file.seek(0)
            shutil.copyfileobj(file, f)

        logger.info(f"Uploaded {filename} to {file_path}")
        return str(file_path)

    def list_files(self, upload_id: str) -> List[Dict[str, Any]]:
        """List files in upload batch directory."""
        batch_path = self._get_batch_path(upload_id)

        if not batch_path.exists():
            return []

        files = []
        for file_path in batch_path.iterdir():
            if file_path.is_file():
                files.append(
                    {
                        "filename": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                    }
                )

        return files

    def get_file_path(self, upload_id: str, filename: str) -> str:
        """Get full path to file."""
        return str(self._get_batch_path(upload_id) / filename)

    def get_file_paths(self, upload_id: str) -> List[str]:
        """Get all file paths for upload batch."""
        files = self.list_files(upload_id)
        return [f["path"] for f in files]

    def delete_batch(self, upload_id: str) -> bool:
        """Delete entire upload batch directory."""
        batch_path = self._get_batch_path(upload_id)

        if batch_path.exists():
            shutil.rmtree(batch_path)
            logger.info(f"Deleted batch {upload_id}")
            return True

        return False

    def file_exists(self, upload_id: str, filename: str) -> bool:
        """Check if file exists."""
        file_path = self._get_batch_path(upload_id) / filename
        return file_path.exists()


class S3Storage(StorageBackend):
    """Amazon S3 storage for production."""

    def __init__(self):
        """Initialize S3 storage with boto3."""
        import boto3

        self.s3_client = boto3.client("s3")
        self.bucket_name = os.getenv("AWS_S3_BUCKET")

        if not self.bucket_name:
            raise ValueError("AWS_S3_BUCKET environment variable not set")

    def _get_s3_key(self, upload_id: str, filename: str) -> str:
        """Generate S3 key for file."""
        return f"uploads/{upload_id}/{filename}"

    def upload(self, file: BinaryIO, upload_id: str, filename: str) -> str:
        """Upload file to S3."""
        s3_key = self._get_s3_key(upload_id, filename)

        file.seek(0)
        self.s3_client.upload_fileobj(
            file, self.bucket_name, s3_key, ExtraArgs={"ServerSideEncryption": "AES256"}
        )

        logger.info(f"Uploaded {filename} to S3: {s3_key}")
        return s3_key

    def list_files(self, upload_id: str) -> List[Dict[str, Any]]:
        """List files in S3 with given prefix."""
        prefix = f"uploads/{upload_id}/"

        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket_name, Prefix=prefix
        )

        files = []
        if "Contents" in response:
            for obj in response["Contents"]:
                filename = obj["Key"].split("/")[-1]
                if filename:  # Skip directory markers
                    files.append(
                        {"filename": filename, "path": obj["Key"], "size": obj["Size"]}
                    )

        return files

    def get_file_path(self, upload_id: str, filename: str) -> str:
        """
        Get S3 presigned URL for file access.

        For internal processing, we'll use the S3 key directly.
        """
        return self._get_s3_key(upload_id, filename)

    def get_file_paths(self, upload_id: str) -> List[str]:
        """Get all S3 keys for upload batch."""
        files = self.list_files(upload_id)
        return [f["path"] for f in files]

    def delete_batch(self, upload_id: str) -> bool:
        """Delete all files in S3 batch."""
        files = self.list_files(upload_id)

        if not files:
            return False

        # Delete objects in batch
        objects = [{"Key": f["path"]} for f in files]

        response = self.s3_client.delete_objects(
            Bucket=self.bucket_name, Delete={"Objects": objects}
        )

        logger.info(f"Deleted {len(objects)} files from S3 batch {upload_id}")
        return "Deleted" in response

    def file_exists(self, upload_id: str, filename: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name, Key=self._get_s3_key(upload_id, filename)
            )
            return True
        except Exception:
            return False

    def download_to_temp(self, upload_id: str, filename: str) -> Path:
        """
        Download S3 file to temporary location for processing.

        Args:
            upload_id: Unique identifier for the upload batch
            filename: Name of the file

        Returns:
            Path: Path to temporary file
        """
        import tempfile

        s3_key = self._get_s3_key(upload_id, filename)

        # Create temp file with same extension
        suffix = Path(filename).suffix
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_path = Path(temp_file.name)

        # Download from S3
        self.s3_client.download_file(self.bucket_name, s3_key, str(temp_path))

        return temp_path

    def download_batch_to_temp(self, upload_id: str) -> List[Path]:
        """
        Download all files in batch to temporary directory.

        Args:
            upload_id: Unique identifier for the upload batch

        Returns:
            List[Path]: Paths to temporary files
        """
        files = self.list_files(upload_id)
        temp_paths = []

        for file_info in files:
            temp_path = self.download_to_temp(upload_id, file_info["filename"])
            temp_paths.append(temp_path)

        return temp_paths
