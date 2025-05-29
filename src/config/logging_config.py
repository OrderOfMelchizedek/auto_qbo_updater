"""
Logging configuration for the FOM to QBO application.

This module handles the setup of comprehensive logging for both
development and production environments.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Tuple


def setup_logging(app=None) -> Tuple[logging.Logger, logging.Logger]:
    """
    Configure comprehensive logging for development and production.

    Args:
        app: Flask application instance (optional)

    Returns:
        Tuple of (main_logger, audit_logger)
    """
    # Determine log level based on environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    is_production = os.getenv("FLASK_ENV", "development") == "production"

    # Get log directory from app config or environment
    if app:
        log_dir = app.config.get("LOG_DIR", "logs")
    else:
        log_dir = os.getenv("LOG_DIR", "logs")

    # Create logs directory if it doesn't exist
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        # In production (like Heroku), we may not have write access to create directories
        print(f"Warning: Could not create logs directory: {e}")
        # Continue without file logging

    # Enhanced format with more context
    detailed_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
    )
    simple_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler configuration
    console_handler = logging.StreamHandler(sys.stdout)
    if is_production:
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(simple_format)
    else:
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(detailed_format)
    root_logger.addHandler(console_handler)

    # File handlers - only add if we can write to disk
    if os.path.exists(log_dir) or not is_production:
        try:
            # General application log
            app_handler = RotatingFileHandler(
                os.path.join(log_dir, "fom_qbo.log"), maxBytes=10485760, backupCount=5, encoding="utf-8"  # 10MB
            )
            app_handler.setLevel(logging.INFO)
            app_handler.setFormatter(detailed_format)
            root_logger.addHandler(app_handler)

            # Error-only log for monitoring
            error_handler = RotatingFileHandler(
                os.path.join(log_dir, "errors.log"), maxBytes=5242880, backupCount=3, encoding="utf-8"  # 5MB
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(detailed_format)
            root_logger.addHandler(error_handler)

            # Audit log for security events
            audit_handler = RotatingFileHandler(
                os.path.join(log_dir, "audit.log"), maxBytes=5242880, backupCount=10, encoding="utf-8"  # 5MB
            )
            audit_handler.setLevel(logging.INFO)
            audit_formatter = logging.Formatter("%(asctime)s - AUDIT - %(levelname)s - %(message)s")
            audit_handler.setFormatter(audit_formatter)

            # Create separate audit logger
            audit_logger = logging.getLogger("audit")
            audit_logger.addHandler(audit_handler)
            audit_logger.setLevel(logging.INFO)
        except Exception as e:
            print(f"Warning: Could not create file handlers: {e}")
            # Continue with console logging only
            audit_logger = logging.getLogger("audit")
            audit_logger.addHandler(console_handler)
            audit_logger.setLevel(logging.INFO)
    else:
        # In production without file logging, use console for audit
        audit_logger = logging.getLogger("audit")
        audit_logger.addHandler(console_handler)
        audit_logger.setLevel(logging.INFO)

    audit_logger.propagate = False

    # Reduce noise from external libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # Get logger for the main app or caller
    if app:
        main_logger = logging.getLogger(app.name)
    else:
        main_logger = logging.getLogger("fom_qbo")

    return main_logger, audit_logger


def get_audit_logger() -> logging.Logger:
    """
    Get the audit logger instance.

    Returns:
        Audit logger
    """
    return logging.getLogger("audit")


def get_app_logger() -> logging.Logger:
    """
    Get the main application logger instance.

    Returns:
        Main application logger
    """
    return logging.getLogger("fom_qbo")
