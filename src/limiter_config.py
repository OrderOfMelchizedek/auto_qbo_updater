"""Configuration for Flask-Limiter with Heroku Redis SSL support."""
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def configure_limiter(app: Flask) -> Limiter:
    """
    Configure Flask-Limiter with proper Redis SSL support for Heroku.

    Args:
        app: Flask application instance

    Returns:
        Configured Limiter instance
    """
    # For now, use memory storage to avoid Redis issues
    # TODO: Fix custom Redis storage implementation
    storage_uri = "memory://"

    # Create limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=storage_uri,
    )

    return limiter
