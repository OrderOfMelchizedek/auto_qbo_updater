"""
Configuration module for selecting storage and session backends.

Automatically chooses between local (development) and cloud (production) backends.
"""
import logging
import os
from typing import Tuple

from .session import LocalSession, RedisSession, SessionBackend
from .storage import LocalStorage, S3Storage, StorageBackend

logger = logging.getLogger(__name__)


def get_backends() -> Tuple[StorageBackend, SessionBackend]:
    """
    Get appropriate storage and session backends based on environment.

    Returns:
        Tuple of (StorageBackend, SessionBackend) instances
    """
    # Check if we're in production mode (Redis and AWS configured)
    redis_url = os.getenv("REDIS_URL")
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_bucket = os.getenv("AWS_S3_BUCKET")

    if redis_url and aws_access_key and aws_secret_key and aws_bucket:
        # Production mode
        logger.info("Using production backends: S3 storage and Redis session")
        try:
            storage: StorageBackend = S3Storage()
            session: SessionBackend = RedisSession()
            return storage, session
        except Exception as e:
            logger.error(f"Failed to initialize production backends: {e}")
            logger.info("Falling back to local backends")

    # Development mode
    logger.info("Using development backends: Local storage and JSON session")
    dev_storage: StorageBackend = LocalStorage()
    dev_session: SessionBackend = LocalSession()

    return dev_storage, dev_session


# Global instances
storage_backend, session_backend = get_backends()


# Configuration settings
class Config:
    """Application configuration settings."""

    # File upload settings
    MAX_FILES_PER_UPLOAD = 20
    MAX_FILE_SIZE_MB = 20
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".csv"}

    # Upload ID format
    UPLOAD_ID_PREFIX = "batch"

    @staticmethod
    def is_allowed_file(filename: str) -> bool:
        """Check if file extension is allowed."""
        from pathlib import Path

        return Path(filename).suffix.lower() in Config.ALLOWED_EXTENSIONS

    @staticmethod
    def generate_upload_id() -> str:
        """Generate unique upload ID with timestamp."""
        from datetime import datetime

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        return f"{Config.UPLOAD_ID_PREFIX}_{timestamp}"
