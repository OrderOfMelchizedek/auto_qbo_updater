"""S3 storage service for document management."""
import logging
from typing import BinaryIO, Optional

import boto3
from botocore.exceptions import ClientError

from src.config.settings import settings
from src.utils.exceptions import DonationProcessingError

logger = logging.getLogger(__name__)


class S3StorageError(DonationProcessingError):
    """Exception raised for S3 storage operations."""

    pass


class S3Service:
    """Service for managing document storage in AWS S3."""

    def __init__(self):
        """Initialize S3 service with configured credentials."""
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION,
        )

    def upload_file(self, file_object: BinaryIO, key: str) -> str:
        """
        Upload a file to S3.

        Args:
            file_object: File-like object to upload
            key: S3 object key (path)

        Returns:
            The S3 key of the uploaded file

        Raises:
            S3StorageError: If upload fails
        """
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_object,
                ServerSideEncryption="AES256",
            )
            logger.info(f"Successfully uploaded file to S3: {key}")
            return key
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise S3StorageError(
                "Failed to upload file to S3", details={"key": key, "error": str(e)}
            )

    def download_file(self, key: str) -> bytes:
        """
        Download a file from S3.

        Args:
            key: S3 object key (path)

        Returns:
            File content as bytes

        Raises:
            S3StorageError: If download fails or file not found
        """
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            content = response["Body"].read()
            logger.info(f"Successfully downloaded file from S3: {key}")
            return content
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise S3StorageError(
                    "File not found in S3", details={"key": key, "error": str(e)}
                )
            logger.error(f"Failed to download file from S3: {e}")
            raise S3StorageError(
                "Failed to download file from S3",
                details={"key": key, "error": str(e)},
            )

    def delete_file(self, key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            key: S3 object key (path)

        Returns:
            True if deletion was successful

        Raises:
            S3StorageError: If deletion fails
        """
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Successfully deleted file from S3: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise S3StorageError(
                "Failed to delete file from S3", details={"key": key, "error": str(e)}
            )

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for temporary access to a file.

        Args:
            key: S3 object key (path)
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL string or None if generation fails
        """
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
            logger.info(f"Generated presigned URL for: {key}")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    def list_files(self, prefix: str = "") -> list:
        """
        List files in S3 with optional prefix filter.

        Args:
            prefix: Filter files by prefix (folder path)

        Returns:
            List of file keys
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=prefix
            )
            if "Contents" in response:
                return [obj["Key"] for obj in response["Contents"]]
            return []
        except ClientError as e:
            logger.error(f"Failed to list files in S3: {e}")
            return []
