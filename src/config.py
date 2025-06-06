"""
Configuration module for selecting storage and session backends.

Automatically chooses between local (development) and cloud (production) backends.
"""
import base64
import logging
import os
from pathlib import Path
from typing import Tuple

from cryptography.fernet import Fernet
from dotenv import load_dotenv

from .session import LocalSession, RedisSession, SessionBackend
from .storage import LocalStorage, S3Storage, StorageBackend

# Load environment variables
load_dotenv()

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

    # QuickBooks OAuth2 settings
    QBO_CLIENT_ID = os.getenv("QBO_CLIENT_ID", "")
    QBO_CLIENT_SECRET = os.getenv("QBO_CLIENT_SECRET", "")
    QBO_REDIRECT_URI = os.getenv("QBO_REDIRECT_URI", "")
    QBO_ENVIRONMENT = os.getenv("QBO_ENVIRONMENT", "sandbox")  # sandbox or production

    # Encryption key for token storage
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

    @staticmethod
    def is_allowed_file(filename: str) -> bool:
        """Check if file extension is allowed."""
        return Path(filename).suffix.lower() in Config.ALLOWED_EXTENSIONS

    @staticmethod
    def generate_upload_id() -> str:
        """Generate unique upload ID with timestamp."""
        from datetime import datetime

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        return f"{Config.UPLOAD_ID_PREFIX}_{timestamp}"

    @staticmethod
    def get_or_create_encryption_key() -> bytes:
        """Get or create encryption key for token storage."""
        if Config.ENCRYPTION_KEY:
            # Use provided key (must be URL-safe base64 encoded)
            try:
                return base64.urlsafe_b64decode(Config.ENCRYPTION_KEY)
            except Exception:
                logger.warning("Invalid ENCRYPTION_KEY format, generating new one")

        # Generate new key if not provided or invalid
        key = Fernet.generate_key()
        logger.warning(
            f"Generated new encryption key. Add to .env: ENCRYPTION_KEY={key.decode()}"
        )
        return key
