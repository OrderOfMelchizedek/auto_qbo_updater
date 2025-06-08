"""
Configuration module for selecting storage and session backends.

Automatically chooses between local (development) and cloud (production) backends.
"""
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
    # Check for Redis availability
    redis_url = os.getenv("REDIS_URL")

    # Check for AWS S3 configuration
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_bucket = os.getenv("AWS_S3_BUCKET")

    # Initialize storage backend
    if aws_access_key and aws_secret_key and aws_bucket:
        logger.info("Using S3 storage backend")
        try:
            storage: StorageBackend = S3Storage()
        except Exception as e:
            logger.error(f"Failed to initialize S3 storage: {e}")
            logger.info("Falling back to local storage")
            storage = LocalStorage()
    else:
        logger.info("Using local storage backend")
        storage = LocalStorage()

    # Initialize session backend - use Redis if available
    if redis_url:
        logger.info("Using Redis session backend")
        try:
            session: SessionBackend = RedisSession()
        except Exception as e:
            logger.error(f"Failed to initialize Redis session: {e}")
            logger.info("Falling back to local session")
            session = LocalSession()
    else:
        logger.info("Using local JSON session backend")
        session = LocalSession()

    return storage, session


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
            # Use provided key directly if it's already a valid Fernet key
            try:
                # Test if it's a valid Fernet key
                Fernet(Config.ENCRYPTION_KEY.encode())
                return Config.ENCRYPTION_KEY.encode()
            except Exception:
                logger.warning("Invalid ENCRYPTION_KEY format, generating new one")

        # Generate new key if not provided or invalid
        key = Fernet.generate_key()
        logger.warning(
            f"Generated new encryption key. Add to .env: ENCRYPTION_KEY={key.decode()}"
        )
        return key
