"""
Session configuration for Flask application.

This module handles the setup of server-side session storage using
Redis for production or filesystem for development.
"""
import os
import tempfile
import redis
from flask_session import Session


def setup_session(app):
    """
    Configure server-side session storage with Redis or filesystem fallback.
    
    Args:
        app: Flask application instance
    """
    redis_url = os.environ.get('REDIS_URL')
    
    if redis_url:
        # Use Redis for production
        try:
            # Parse Redis URL (handles various formats including Heroku's)
            if redis_url.startswith(('redis://', 'rediss://')):
                app.config['SESSION_TYPE'] = 'redis'
                # Handle Heroku Redis SSL URLs
                if redis_url.startswith('rediss://'):
                    # For SSL Redis connections, we need special handling
                    app.config['SESSION_REDIS'] = redis.from_url(
                        redis_url, 
                        ssl_cert_reqs=None
                    )
                else:
                    app.config['SESSION_REDIS'] = redis.from_url(redis_url)
                print("Using Redis for session storage")
            else:
                raise ValueError("Invalid REDIS_URL format")
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            print("Falling back to filesystem session storage")
            _configure_filesystem_sessions(app)
    else:
        # Use filesystem for development
        print("No REDIS_URL found. Using filesystem for session storage (development mode)")
        _configure_filesystem_sessions(app)
    
    # Common session configuration
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'fom_qbo:'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    
    # Initialize Flask-Session
    Session(app)


def _configure_filesystem_sessions(app):
    """
    Configure filesystem-based sessions for development.
    
    Args:
        app: Flask application instance
    """
    session_dir = os.path.join(tempfile.gettempdir(), 'fom_qbo_sessions')
    os.makedirs(session_dir, exist_ok=True)
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = session_dir
    app.config['SESSION_FILE_THRESHOLD'] = 100  # Max number of sessions