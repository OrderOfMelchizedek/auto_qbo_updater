"""Application configuration management using Pydantic settings."""
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    APP_NAME: str = "QuickBooks Donation Manager"
    DEBUG: bool = False
    SECRET_KEY: str = "your_secret_key_here"

    # Google Gemini API
    GEMINI_API_KEY: Optional[str] = None

    # QuickBooks Online API
    QBO_CLIENT_ID: Optional[str] = None
    QBO_CLIENT_SECRET: Optional[str] = None
    QBO_REDIRECT_URI: Optional[str] = None
    QBO_ENVIRONMENT: str = "sandbox"

    # QuickBooks API Settings (for services)
    QUICKBOOKS_CLIENT_ID: Optional[str] = None
    QUICKBOOKS_CLIENT_SECRET: Optional[str] = None
    QUICKBOOKS_REDIRECT_URI: str = "http://localhost:8000/api/quickbooks/callback"
    QUICKBOOKS_BASE_URL: str = "https://sandbox-quickbooks.api.intuit.com"
    QUICKBOOKS_AUTHORIZATION_BASE_URL: str = (
        "https://appcenter.intuit.com/connect/oauth2"
    )
    QUICKBOOKS_TOKEN_URL: str = (
        "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET_NAME: Optional[str] = None
    AWS_S3_REGION: str = "us-east-1"

    # JWT
    JWT_SECRET_KEY: str = "your_jwt_secret_key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # File Upload
    MAX_UPLOAD_FILES: int = 20
    MAX_FILE_SIZE_MB: int = 20

    # Celery
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # Sentry
    SENTRY_DSN: Optional[str] = None

    # Define a model_config to load from a .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def __init__(self, **values):
        """Initialize settings with computed values."""
        super().__init__(**values)
        # Use Redis URL for Celery if not explicitly set
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL
        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL

        # Sync QuickBooks settings (QBO_ prefix vs QUICKBOOKS_ prefix)
        if self.QBO_CLIENT_ID and not self.QUICKBOOKS_CLIENT_ID:
            self.QUICKBOOKS_CLIENT_ID = self.QBO_CLIENT_ID
        if self.QBO_CLIENT_SECRET and not self.QUICKBOOKS_CLIENT_SECRET:
            self.QUICKBOOKS_CLIENT_SECRET = self.QBO_CLIENT_SECRET
        if self.QBO_REDIRECT_URI and not self.QUICKBOOKS_REDIRECT_URI:
            self.QUICKBOOKS_REDIRECT_URI = self.QBO_REDIRECT_URI

        # Set QuickBooks URLs based on environment
        if self.QBO_ENVIRONMENT == "production":
            self.QUICKBOOKS_BASE_URL = "https://quickbooks.api.intuit.com"
        else:
            self.QUICKBOOKS_BASE_URL = "https://sandbox-quickbooks.api.intuit.com"


settings = Settings()
