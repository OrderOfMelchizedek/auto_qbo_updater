from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "QuickBooks Donation Manager"
    DEBUG: bool = False
    SECRET_KEY: str = "your_secret_key_here"

    GEMINI_API_KEY: Optional[str] = None

    QBO_CLIENT_ID: Optional[str] = None
    QBO_CLIENT_SECRET: Optional[str] = None
    QBO_REDIRECT_URI: Optional[str] = None
    QBO_ENVIRONMENT: str = "sandbox"

    REDIS_URL: str = "redis://localhost:6379/0"
    SENTRY_DSN: Optional[str] = None

    # Define a model_config to load from a .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()