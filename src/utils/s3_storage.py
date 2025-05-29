import logging
import os
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Storage:
    """Handle file storage operations with Amazon S3."""

    def __init__(self):
        """Initialize S3 storage client.

        Configures the S3 client using AWS credentials from environment variables
        and sets up the bucket name for storage operations.
        """
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )
        self.bucket_name = os.environ.get("S3_BUCKET_NAME", "fom-qbo-uploads")

    def upload_file(self, file_content: bytes, key: str, content_type: str = "application/octet-stream") -> Dict:
        """Upload a file to S3 and return the reference."""
        try:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=key, Body=file_content, ContentType=content_type)

            logger.info(f"Uploaded file to S3: {key}")

            return {"bucket": self.bucket_name, "key": key, "size": len(file_content)}

        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise

    def download_file(self, key: str) -> bytes:
        """Download a file from S3 and return its content."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)

            content = response["Body"].read()
            logger.info(f"Downloaded file from S3: {key}")

            return content

        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            raise

    def delete_file(self, key: str) -> None:
        """Delete a file from S3."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)

            logger.info(f"Deleted file from S3: {key}")

        except ClientError as e:
            logger.error(f"Failed to delete from S3: {e}")  # nosec B608 - Not SQL
            raise

    def generate_key(self, session_id: str, filename: str) -> str:
        """Generate a unique S3 key for a file."""
        import uuid

        file_id = str(uuid.uuid4())
        return f"uploads/{session_id}/{file_id}_{filename}"
