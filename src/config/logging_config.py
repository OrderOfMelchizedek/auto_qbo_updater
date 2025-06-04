"""Logging configuration for the application."""
import logging
import sys
from typing import Optional

from src.config.settings import settings


def setup_logging(debug: Optional[bool] = None) -> None:
    """
    Configure logging for the application.

    Args:
        debug: Override debug setting from config
    """
    # Use debug parameter or fall back to settings
    is_debug = debug if debug is not None else settings.DEBUG

    # Set log level
    log_level = logging.DEBUG if is_debug else logging.INFO

    # Configure basic logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Silence noisy libraries
    noisy_loggers = [
        "urllib3.connectionpool",
        "boto3",
        "botocore",
        "google.auth",
        "google.auth.transport",
        "google.auth.compute_engine",
    ]

    for logger_name in noisy_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)

    # Set application logger to appropriate level
    app_logger = logging.getLogger("src")
    app_logger.setLevel(log_level)

    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {logging.getLevelName(log_level)}")
