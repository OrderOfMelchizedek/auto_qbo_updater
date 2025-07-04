"""Flask application with donation processing API endpoints."""
import glob
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    make_response,
    redirect,
    request,
    stream_with_context,
)
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from flask_session import Session  # type: ignore

from .config import Config, session_backend, storage_backend
from .customer_matcher import CustomerMatcher
from .job_queue import JobQueue
from .job_tracker import JobTracker
from .limiter_config import configure_limiter, configure_limiter_emergency_disable
from .quickbooks_auth import qbo_auth
from .quickbooks_utils import QuickBooksError
from .redis_retry import warm_connection_pool, warm_session_backend
from .secure_logging import audit_logger, setup_secure_logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Set up secure logging
setup_secure_logging(logger)

# Initialize Flask app
# Check if we're on Heroku (production) or local development
if os.environ.get("DYNO") or os.path.exists(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
):
    # In production, serve static files from React build
    static_folder = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
    )
    app = Flask(__name__, static_folder=static_folder, static_url_path="")
    logger.info(f"Flask initialized with static folder: {static_folder}")
else:
    # In development, use default static folder
    app = Flask(__name__)
    logger.info("Flask initialized for development mode")

# Job queue will be initialized after Redis client is created

# Initialize rate limiter with proper Redis SSL support
try:
    limiter = configure_limiter(app)
    logger.info("✓ Flask-Limiter initialized successfully")
except Exception as e:
    logger.error(f"✗ Flask-Limiter initialization failed: {e}")
    logger.warning("Using emergency limiter configuration (rate limiting disabled)")
    limiter = configure_limiter_emergency_disable(app)


app.config["MAX_CONTENT_LENGTH"] = (
    Config.MAX_FILE_SIZE_BYTES * Config.MAX_FILES_PER_UPLOAD
)

# Disable caching for development
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Configure Flask sessions
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32).hex())
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

# Use Redis for sessions in production, filesystem for local dev
redis_url = os.environ.get("REDIS_URL")
if redis_url:
    from .redis_connection import create_redis_client

    redis_client = create_redis_client(
        decode_responses=False, max_connections=5  # Flask-Session needs bytes
    )
    if redis_client:
        app.config["SESSION_REDIS"] = redis_client
        app.config["SESSION_TYPE"] = "redis"
        logger.info("✓ Redis initialized for Flask-Session")

        # Pre-warm Redis connections to avoid SSL errors during requests
        if warm_connection_pool(redis_client, pool_size=3):
            logger.info("✓ Redis connection pool pre-warmed successfully")
        else:
            logger.warning("⚠️ Failed to pre-warm all Redis connections")
    else:
        app.config["SESSION_TYPE"] = "filesystem"
        logger.info("⚠️ Flask-Session using filesystem (Redis connection failed)")
else:
    app.config["SESSION_TYPE"] = "filesystem"
    logger.info("⚠️ Flask-Session using filesystem (no REDIS_URL)")

# SIMPLE SOLUTION: Disable JobTracker in web app to avoid Redis connection limits
# Progress tracking is not essential - worker processes files without it
# This keeps us well under the Redis connection limit
job_tracker = JobTracker()  # Initialize without Redis connection
logger.info("✓ JobTracker disabled in web app to prevent Redis connection issues")

# Initialize job queue for replacing Celery
job_queue = None  # type: ignore
if redis_url:
    job_queue = JobQueue(redis_client)
    logger.info("✓ Job queue initialized with Redis connection")
else:
    # Fallback for local development without Redis
    logger.warning("⚠️ Job queue disabled - no Redis connection")

# Initialize Flask-Session
Session(app)

# Pre-warm session backend Redis connection
if warm_session_backend():
    logger.info("✓ Session backend Redis connection pre-warmed")
else:
    logger.warning("⚠️ Failed to pre-warm session backend connection")

# Configure secure cookies for production
if os.environ.get("DYNO"):
    # In production on Heroku
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_NAME"] = "qbo_session"

# Enable CORS for all routes with specific configuration
# In production, add the Heroku domain to allowed origins
allowed_origins = ["http://localhost:3000", "http://localhost:5000"]

# Add production domain if available
production_domain = os.environ.get("PRODUCTION_DOMAIN")
if production_domain:
    allowed_origins.append(f"https://{production_domain}")
    allowed_origins.append(f"http://{production_domain}")

# Add custom subdomain
allowed_origins.append("https://auto-qbo-updater.mwangazapartnership.org")
allowed_origins.append("http://auto-qbo-updater.mwangazapartnership.org")

# If on Heroku, also add the Heroku app domain
if os.environ.get("DYNO"):
    app_name = os.environ.get("APP_NAME", "auto-qbo-updater")
    allowed_origins.append(f"https://{app_name}.herokuapp.com")
    allowed_origins.append(f"https://{app_name}-*.herokuapp.com")
    # Also add the specific Heroku domain
    allowed_origins.append("https://auto-qbo-updater-b8a695c1c287.herokuapp.com")

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Session-ID"],
            "supports_credentials": True,
        }
    },
)


# HTTPS redirect and security headers for production
if os.environ.get("DYNO"):

    @app.before_request
    def force_https():
        """Redirect HTTP to HTTPS in production."""
        # Skip if already HTTPS or if it's a health check
        if request.path == "/api/health":
            return None

        # Heroku passes the original protocol via X-Forwarded-Proto header
        if request.headers.get("X-Forwarded-Proto") == "http":
            # Build the HTTPS URL
            url = request.url.replace("http://", "https://", 1)
            return redirect(url, code=301)

    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses in production."""
        # Strict Transport Security - enforce HTTPS for 1 year
        response.headers[
            "Strict-Transport-Security"
        ] = "max-age=31536000; includeSubDomains"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"

        # XSS Protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Basic Content Security Policy
        csp = (
            "default-src 'self' https:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline';"
        )
        response.headers["Content-Security-Policy"] = csp

        return response


@app.route("/api/")
def hello():
    """Return API information."""
    return jsonify(
        {
            "name": "QuickBooks Donation Manager API",
            "version": "1.0.0",
            "endpoints": {
                "/api/upload": "POST - Upload donation documents",
                "/api/process": "POST - Process uploaded documents (async)",
                "/api/jobs/{job_id}": "GET - Get job status and results",
                "/api/jobs/{job_id}/stream": "GET - Stream job progress (SSE)",
                "/api/health": "GET - Health check",
                "/api/auth/qbo/authorize": "GET - Get OAuth2 authorization URL",
                "/api/auth/qbo/callback": "GET - Handle OAuth2 callback",
                "/api/auth/qbo/refresh": "POST - Refresh access token",
                "/api/auth/qbo/revoke": "POST - Revoke tokens",
                "/api/auth/qbo/status": "GET - Check authentication status",
            },
        }
    )


@app.route("/api/session", methods=["GET"])
def get_session():
    """Get or create a secure session."""
    from flask import session

    # Use a consistent session ID stored in Flask session
    # This ID is used for QuickBooks token storage
    if "app_session_id" not in session:
        session["app_session_id"] = Config.generate_upload_id()
        session.permanent = True

        # Audit log new session
        audit_logger.log_security_event(
            "session_created",
            session_id=session["app_session_id"],
            details={"ip": request.remote_addr},
        )

    return jsonify({"success": True, "session_id": session["app_session_id"]})


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    health_info = {
        "status": "healthy",
        "storage": type(storage_backend).__name__,
        "session": type(session_backend).__name__,
        "local_dev_mode": os.getenv("LOCAL_DEV_MODE") == "true",
        "qbo_environment": Config.QBO_ENVIRONMENT,
    }

    # Test CSV loading in local dev mode
    if os.getenv("LOCAL_DEV_MODE") == "true":
        try:
            csv_path = (
                Path(__file__).parent.parent
                / "src/tests/test_files/customer_contact_list.csv"
            )
            health_info["csv_exists"] = csv_path.exists()
            health_info["csv_path"] = str(csv_path)

            if csv_path.exists():
                # Try to count lines
                with open(csv_path, "r") as f:
                    line_count = sum(1 for line in f)
                health_info["csv_lines"] = line_count
        except Exception as e:
            health_info["csv_error"] = str(e)

    return jsonify(health_info)


@app.route("/api/queue/stats", methods=["GET"])
def queue_stats():
    """Get job queue statistics."""
    try:
        stats = (
            job_queue.get_queue_stats() if job_queue else {"error": "Queue disabled"}
        )
        return jsonify({"success": True, "data": stats})
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# QuickBooks OAuth2 endpoints
@app.route("/api/auth/qbo/authorize", methods=["GET"])
@limiter.limit("5 per minute")
def qbo_authorize():
    """
    Generate QuickBooks OAuth2 authorization URL.

    Returns:
        JSON with authorization URL and state
    """
    try:
        if qbo_auth is None:
            return jsonify({"success": False, "error": "OAuth2 not configured"}), 500

        # Get session ID from Flask session to ensure consistency
        from flask import session

        if "app_session_id" not in session:
            session["app_session_id"] = Config.generate_upload_id()
            session.permanent = True

        session_id = session["app_session_id"]

        # Generate authorization URL
        auth_url, state = qbo_auth.get_authorization_url(session_id)

        logger.info("Generated QuickBooks auth URL")

        # Audit log
        audit_logger.log_security_event(
            "oauth_init", session_id=session_id, details={"ip": request.remote_addr}
        )

        return jsonify(
            {
                "success": True,
                "data": {
                    "auth_url": auth_url,
                    "state": state,
                    "session_id": session_id,
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to generate auth URL: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/auth/qbo/callback", methods=["GET"])
@limiter.limit("10 per minute")
def qbo_callback():
    """
    Handle OAuth2 callback from QuickBooks.

    Query params:
        code: Authorization code
        state: CSRF state token
        realmId: QuickBooks company ID
    """
    try:
        # Get parameters from query string
        code = request.args.get("code")
        state = request.args.get("state")
        realm_id = request.args.get("realmId")
        error = request.args.get("error")
        error_description = request.args.get("error_description")

        # Log the callback for debugging
        logger.info("OAuth2 callback received")

        # Handle OAuth errors from QuickBooks
        if error:
            logger.error(f"OAuth2 error: {error} - {error_description}")
            # Audit log auth failure
            audit_logger.log_auth_attempt(
                session_id=request.headers.get("X-Session-ID", "unknown"),
                ip_address=request.remote_addr,
                success=False,
                reason=f"OAuth error: {error}",
            )
            # Redirect to React app with error
            from flask import redirect

            return redirect(f"/auth/callback?success=false&error={error}")

        if not all([code, state, realm_id]):
            logger.error(
                f"Missing parameters - code: {bool(code)}, "
                f"state: {bool(state)}, realm_id: {bool(realm_id)}"
            )
            return (
                jsonify({"success": False, "error": "Missing required parameters"}),
                400,
            )

        # Get session ID from header (optional now)
        session_id = request.headers.get("X-Session-ID")
        logger.info("Processing OAuth callback")

        # Exchange code for tokens (session_id can be extracted from state)
        result = qbo_auth.exchange_authorization_code(
            code=code, realm_id=realm_id, state=state, session_id=session_id
        )

        # Audit log successful auth
        audit_logger.log_auth_attempt(
            session_id=result.get("session_id", session_id or "unknown"),
            ip_address=request.remote_addr,
            success=True,
            reason="OAuth callback successful",
        )

        # In production, redirect to React callback page instead of returning JSON
        # The React app will handle the UI update
        if (
            request.accept_mimetypes.best == "text/html"
            or "appcenter.intuit.com" in request.headers.get("Referer", "")
        ):
            # Redirect to React callback page with success indicator
            from flask import redirect

            return redirect(f"/auth/callback?success=true&realm_id={realm_id}")

        # For API calls (from React), return JSON
        return jsonify({"success": True, "data": result})

    except ValueError as e:
        logger.error(f"OAuth2 callback validation error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"OAuth2 callback error: {e}")
        return jsonify({"success": False, "error": "Authentication failed"}), 500


@app.route("/api/auth/qbo/refresh", methods=["POST"])
@limiter.limit("20 per hour")
def qbo_refresh():
    """
    Refresh expired access token.

    Requires:
        X-Session-ID header
    """
    try:
        # Get session ID from header
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return jsonify({"success": False, "error": "Missing session ID"}), 400

        # Refresh token
        result = qbo_auth.refresh_access_token(session_id)

        # Audit log
        audit_logger.log_token_refresh(session_id=session_id, success=True)

        return jsonify({"success": True, "data": result})

    except ValueError as e:
        logger.error("Token refresh error")
        # Audit log failure
        audit_logger.log_token_refresh(
            session_id=session_id if "session_id" in locals() else "unknown",
            success=False,
            error=str(e),
        )
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({"success": False, "error": "Failed to refresh token"}), 500


@app.route("/api/auth/qbo/revoke", methods=["POST"])
@limiter.limit("5 per hour")
def qbo_revoke():
    """
    Revoke QuickBooks access tokens.

    Requires:
        X-Session-ID header
    """
    try:
        # Get session ID from header
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return jsonify({"success": False, "error": "Missing session ID"}), 400

        # Revoke tokens
        success = qbo_auth.revoke_tokens(session_id)

        # Audit log
        if success:
            audit_logger.log_token_revoke(
                session_id=session_id, ip_address=request.remote_addr
            )

        return jsonify(
            {
                "success": success,
                "message": "Tokens revoked" if success else "Revocation failed",
            }
        )

    except Exception as e:
        logger.error(f"Token revocation error: {e}")
        return jsonify({"success": False, "error": "Failed to revoke tokens"}), 500


@app.route("/api/auth/qbo/status", methods=["GET"])
def qbo_status():
    """
    Check QuickBooks authentication status.

    Uses Flask session for consistent session management.
    """
    try:
        from flask import session

        # Get session ID from Flask session
        session_id = session.get("app_session_id")
        if not session_id:
            return jsonify({"success": True, "data": {"authenticated": False}})

        # Get auth status
        status = qbo_auth.get_auth_status(session_id)

        return jsonify({"success": True, "data": status})

    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({"success": True, "data": {"authenticated": False}})


@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id):
    """
    Get job status and results.

    Returns:
        JSON with job status, progress, and results if completed
    """
    # Check if job is in completed queue
    if job_queue and job_queue.is_job_completed(job_id):
        # Get the job data to find upload_id
        job_data = job_queue.get_job_data(job_id)
        upload_id = job_data.get("upload_id") if job_data else None

        # If we have the upload_id, fetch the actual results
        if upload_id:
            metadata = session_backend.get_upload_metadata(upload_id)
            if metadata and metadata.get("status") == "completed":
                return jsonify(
                    {
                        "success": True,
                        "data": {
                            "id": job_id,
                            "status": "completed",
                            "stage": "complete",
                            "progress": 100,
                            "message": "Processing complete!",
                            "upload_id": upload_id,
                            "result": {
                                "donations": metadata.get("donations", []),
                                "metadata": metadata.get("summary", {}),
                            },
                        },
                    }
                )

        # Fallback if we can't get results
        return jsonify(
            {
                "success": True,
                "data": {
                    "id": job_id,
                    "status": "completed",
                    "stage": "complete",
                    "progress": 100,
                    "message": "Processing complete!",
                    "upload_id": upload_id,
                },
            }
        )

    # Check if job is in failed queue
    if job_queue and job_queue.is_job_failed(job_id):
        return jsonify(
            {
                "success": True,
                "data": {
                    "id": job_id,
                    "status": "failed",
                    "stage": "error",
                    "progress": 0,
                    "message": "Processing failed. Please try again.",
                },
            }
        )

    # Otherwise, assume it's still processing
    return jsonify(
        {
            "success": True,
            "data": {
                "id": job_id,
                "status": "processing",
                "stage": "processing",
                "progress": 50,
                "message": (
                    "Processing donations in background. "
                    "Results will be available soon."
                ),
            },
        }
    )


@app.route("/api/jobs/<job_id>/stream", methods=["GET"])
def stream_job_events(job_id):
    """
    Stream job progress events using Server-Sent Events.

    Returns:
        SSE stream of job updates
    """

    def generate():
        # SIMPLE SOLUTION: Without JobTracker Redis pub/sub,
        # we can't stream real updates
        # Send a single "processing" event and close the stream
        # The UI should fall back to polling

        # Send initial status
        initial_data = {
            "type": "initial",
            "job": {
                "id": job_id,
                "status": "processing",
                "stage": "processing",
                "progress": 50,
            },
        }
        yield f"data: {json.dumps(initial_data)}\n\n"

        # Send heartbeat and close
        yield ": heartbeat\n\n"

        # Send completion event to close the stream
        completion_data = {
            "type": "status",
            "status": "processing",
            "message": "Job processing in background",
        }
        yield f"data: {json.dumps(completion_data)}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Connection": "keep-alive",
        },
    )


@app.route("/api/debug/build", methods=["GET"])
def debug_build():
    """Debug endpoint to check build directory contents."""
    build_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
    )

    result = {
        "build_dir": build_dir,
        "exists": os.path.exists(build_dir),
        "static_folder": app.static_folder,
        "static_folder_exists": os.path.exists(app.static_folder)
        if app.static_folder
        else False,
        "files": [],
    }

    if os.path.exists(build_dir):
        all_files = glob.glob(os.path.join(build_dir, "**/*"), recursive=True)
        for file_path in all_files:
            if os.path.isfile(file_path):
                relative_path = os.path.relpath(file_path, build_dir)
                result["files"].append(relative_path)

    return jsonify(result)


@app.route("/api/upload", methods=["POST"])
@limiter.limit("30 per hour")
def upload_files():
    """
    Upload donation documents.

    Accepts multipart/form-data with up to 20 files.
    Files must be JPEG, PNG, PDF, or CSV format, max 20MB each.

    Returns:
        JSON response with upload_id and file information
    """
    try:
        # Check if files were provided
        if "files" not in request.files:
            return jsonify({"success": False, "error": "No files provided"}), 400

        files = request.files.getlist("files")

        # Validate number of files
        if len(files) == 0:
            return jsonify({"success": False, "error": "No files selected"}), 400

        if len(files) > Config.MAX_FILES_PER_UPLOAD:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": (
                            f"Too many files. Maximum is "
                            f"{Config.MAX_FILES_PER_UPLOAD}"
                        ),
                    }
                ),
                400,
            )

        # Generate upload ID
        upload_id = Config.generate_upload_id()
        uploaded_files = []

        # Process each file
        for file in files:
            # Skip empty files
            if file.filename == "":
                continue

            # Validate file type
            if not Config.is_allowed_file(file.filename):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": (
                                f"Invalid file type: {file.filename}. "
                                f"Allowed types: "
                                f"{', '.join(Config.ALLOWED_EXTENSIONS)}"
                            ),
                        }
                    ),
                    400,
                )

            # Secure the filename
            original_filename = file.filename
            secure_name = secure_filename(file.filename)

            # Ensure unique filename
            stored_filename = f"{len(uploaded_files)}_{secure_name}"

            # Upload to storage backend
            try:
                storage_backend.upload(file, upload_id, stored_filename)

                uploaded_files.append(
                    {
                        "original_name": original_filename,
                        "stored_name": stored_filename,
                        "size": file.content_length or 0,
                    }
                )

                logger.info(f"Uploaded {original_filename} as {stored_filename}")

            except Exception as e:
                logger.error(f"Failed to upload {original_filename}: {e}")
                # Clean up any uploaded files
                storage_backend.delete_batch(upload_id)
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Failed to upload {original_filename}: {str(e)}",
                        }
                    ),
                    500,
                )

        # Store upload metadata
        metadata = {
            "upload_id": upload_id,
            "files": uploaded_files,
            "total_files": len(uploaded_files),
            "status": "uploaded",
        }

        session_backend.store_upload_metadata(upload_id, metadata)

        return jsonify(
            {"success": True, "data": {"upload_id": upload_id, "files": uploaded_files}}
        )

    except RequestEntityTooLarge:
        return (
            jsonify(
                {
                    "success": False,
                    "error": (
                        f"File too large. Maximum size is "
                        f"{Config.MAX_FILE_SIZE_MB}MB per file"
                    ),
                }
            ),
            413,
        )

    except Exception as e:
        logger.error(f"Upload error: {e}")
        return (
            jsonify({"success": False, "error": "An error occurred during upload"}),
            500,
        )


@app.route("/api/process", methods=["POST"])
def process_files():
    """
    Process uploaded donation documents asynchronously.

    Expects JSON with upload_id.
    Queues job for background processing.

    Returns:
        JSON response with job_id for tracking
    """
    try:
        # Get upload_id from request
        data = request.get_json()
        if not data or "upload_id" not in data:
            return jsonify({"success": False, "error": "upload_id is required"}), 400

        upload_id = data["upload_id"]

        # Get upload metadata
        metadata = session_backend.get_upload_metadata(upload_id)
        if not metadata:
            return jsonify({"success": False, "error": "Upload not found"}), 404

        # Check if already processed
        if metadata.get("status") == "processed":
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "donations": metadata.get("donations", []),
                        "metadata": metadata.get("processing_metadata", {}),
                        "status": "completed",
                    },
                }
            )

        # Get session ID for QuickBooks matching from Flask session
        from flask import session as flask_session

        session_id = flask_session.get("app_session_id")

        # Generate job ID
        job_id = str(uuid.uuid4())

        # SIMPLE SOLUTION: Skip JobTracker to avoid Redis connection limit issues
        # The worker will process files without progress tracking
        # This keeps us under the Redis connection limit

        # Queue the job using our simple Redis queue (no more Celery SSL issues!)
        job_data = {
            "job_id": job_id,
            "upload_id": upload_id,
            "session_id": session_id,
        }

        if job_queue and job_queue.push_job(job_data):
            logger.info(f"Queued job {job_id} for upload {upload_id}")
        else:
            logger.error(f"Failed to queue job {job_id}")
            return jsonify({"success": False, "error": "Failed to queue job"}), 500

        # Return job ID for tracking
        return jsonify(
            {
                "success": True,
                "data": {
                    "job_id": job_id,
                    "status": "queued",
                    "message": "Processing queued",
                },
            }
        )

    except Exception as e:
        logger.error(f"Error processing files: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/uploads/<upload_id>/results", methods=["GET"])
def get_upload_results(upload_id):
    """
    Get processing results for an upload.

    Returns:
        JSON with processed donation data
    """
    try:
        # Get upload metadata which contains the results
        metadata = session_backend.get_upload_metadata(upload_id)

        if not metadata:
            return jsonify({"success": False, "error": "Results not found"}), 404

        # Check if processing is complete
        if metadata.get("status") != "completed":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": (
                            f"Processing status: {metadata.get('status', 'unknown')}"
                        ),
                    }
                ),
                400,
            )

        # Return the results
        return jsonify(
            {
                "success": True,
                "data": {
                    "donations": metadata.get("donations", []),
                    "summary": metadata.get("summary", {}),
                    "processed_at": metadata.get("processed_at"),
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting results for upload {upload_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/search_customers", methods=["GET"])
def search_customers():
    """Search for customers in QuickBooks."""
    try:
        logger.info(f"Search customers endpoint called with args: {request.args}")
        logger.info(f"Headers: {dict(request.headers)}")

        search_term = request.args.get("search_term")
        if not search_term:
            return jsonify({"success": False, "error": "Missing search_term"}), 400

        logger.info(f"Search term: {search_term}")

        # Check for local dev mode
        if os.getenv("LOCAL_DEV_MODE") == "true":
            csv_path = (
                Path(__file__).parent.parent
                / "src/tests/test_files/customer_contact_list.csv"
            )
            logger.info(f"Local dev mode: Using CSV at {csv_path}")

            if not csv_path.exists():
                logger.error(f"CSV file not found at {csv_path}")
                return (
                    jsonify(
                        {"success": False, "error": "Customer data file not found"}
                    ),
                    500,
                )

            try:
                customer_matcher = CustomerMatcher(csv_path=csv_path)
                logger.info("CustomerMatcher created successfully")
            except Exception as e:
                logger.error(f"Failed to create CustomerMatcher: {e}", exc_info=True)
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Failed to initialize customer data: {str(e)}",
                        }
                    ),
                    500,
                )
        else:
            from flask import session as flask_session

            session_id = flask_session.get("app_session_id")
            if not session_id:
                return (
                    jsonify({"success": False, "error": "No active session found"}),
                    400,
                )
            customer_matcher = CustomerMatcher(session_id=session_id)

        try:
            customers = customer_matcher.data_source.search_customer(search_term)
            logger.info(f"Found {len(customers)} customers")
        except Exception as e:
            logger.error(f"Failed to search customers: {e}", exc_info=True)
            return jsonify({"success": False, "error": f"Search failed: {str(e)}"}), 500

        return jsonify({"success": True, "data": customers})

    except QuickBooksError as e:
        logger.error(f"QuickBooks API error in search_customers: {e}")
        return (
            jsonify({"success": False, "error": str(e), "details": e.detail}),
            e.status_code,
        )
    except Exception as e:
        logger.error(f"Unexpected error in search_customers: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


@app.route("/api/manual_match", methods=["POST"])
def manual_match():
    """Manually match a donation to a QuickBooks customer.

    Returns updated donation with QuickBooks customer information.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Invalid JSON payload"}), 400

        original_donation = data.get("donation")
        qb_customer_id = data.get("qb_customer_id")

        if not original_donation or not qb_customer_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Missing 'donation' or 'qb_customer_id'",
                    }
                ),
                400,
            )

        # Check for local dev mode
        if os.getenv("LOCAL_DEV_MODE") == "true":
            csv_path = (
                Path(__file__).parent.parent
                / "src/tests/test_files/customer_contact_list.csv"
            )
            logger.info(f"Local dev mode: Using CSV at {csv_path}")
            customer_matcher = CustomerMatcher(csv_path=csv_path)
        else:
            session_id = request.headers.get("X-Session-ID")
            if not session_id:
                return (
                    jsonify({"success": False, "error": "Missing X-Session-ID header"}),
                    400,
                )
            customer_matcher = CustomerMatcher(session_id=session_id)

        # Fetch the full details of the selected QuickBooks customer
        qb_customer_detail = customer_matcher.data_source.get_customer(qb_customer_id)
        if not qb_customer_detail:
            # This case might be handled by QuickBooksError
            # if get_customer raises it for not found
            return (
                jsonify(
                    {
                        "success": False,
                        "error": (
                            f"QuickBooks customer with ID {qb_customer_id} " "not found"
                        ),
                    }
                ),
                404,
            )

        # Format the fetched customer data
        formatted_qb_customer = customer_matcher.data_source.format_customer_data(
            qb_customer_detail
        )

        # Prepare original donation data for merge_customer_data
        # merge_customer_data expects a dict with "PayerInfo" and "ContactInfo"
        # Assuming original_donation (FinalDisplayDonation) has
        # 'payer_info' and 'contact_info' keys
        original_payer_contact_info = {
            "PayerInfo": original_donation.get("payer_info", {}),
            "ContactInfo": original_donation.get("contact_info", {}),
        }

        # Merge the data
        merged_data = customer_matcher.merge_customer_data(
            original_payer_contact_info, formatted_qb_customer
        )

        # Update the original_donation object with the merged data
        # Ensure payer_info exists
        if "payer_info" not in original_donation:
            original_donation["payer_info"] = {}

        original_donation["payer_info"]["customer_ref"] = merged_data.get(
            "customer_ref"
        )
        original_donation["payer_info"]["qb_address"] = merged_data.get("qb_address")
        original_donation["payer_info"]["qb_email"] = merged_data.get("qb_email")
        original_donation["payer_info"]["qb_phone"] = merged_data.get("qb_phone")

        # Update name fields if they are part of customer_ref
        # and need to be directly on payer_info
        # This depends on FinalDisplayDonation structure and
        # what merge_customer_data returns in customer_ref
        if merged_data.get("customer_ref"):
            original_donation["payer_info"]["qb_display_name"] = merged_data[
                "customer_ref"
            ].get("display_name")
            original_donation["payer_info"]["qb_given_name"] = merged_data[
                "customer_ref"
            ].get("given_name")
            original_donation["payer_info"]["qb_family_name"] = merged_data[
                "customer_ref"
            ].get("family_name")
            original_donation["payer_info"]["qb_organization_name"] = merged_data[
                "customer_ref"
            ].get("organization_name")

        # Update status
        if "status" not in original_donation:
            original_donation["status"] = {}

        original_donation["status"]["matched"] = True
        original_donation["status"][
            "new_customer"
        ] = False  # It's a match to an existing customer
        original_donation["status"]["sent_to_qb"] = False  # Not yet sent, just matched
        original_donation["status"][
            "qbo_customer_id"
        ] = qb_customer_id  # Store the customer ID

        # Determine if address was updated by comparing old and new, if necessary
        # For now, if updates_needed is true, we can assume some edit/update happened.
        # The 'updates_needed' from merge_customer_data can
        # signify if QBO data differs from original.
        updates_needed = merged_data.get("updates_needed", False)
        if updates_needed:
            original_donation["status"]["edited"] = True  # Indicates a change was made
            # We might need more fine-grained logic for address_updated
            # if original_donation had an address
            # and it changed. For now, let's assume 'edited' covers this.
            # original_donation["status"]["address_updated"] = True
            # If qb_address changed specifically

        return jsonify({"success": True, "data": original_donation})

    except QuickBooksError as e:
        logger.error(f"QuickBooks API error in manual_match: {e}")
        return (
            jsonify({"success": False, "error": str(e), "details": e.detail}),
            e.status_code,
        )
    except Exception as e:
        logger.error(f"Error in manual_match: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return (
            jsonify({"success": False, "error": "Failed to process manual match"}),
            500,
        )


@app.route("/api/accounts", methods=["GET"])
def get_accounts():
    """
    Get all accounts from QuickBooks.

    Requires X-Session-ID header for QuickBooks authentication (in production).
    Returns list of accounts with their types and names.
    """
    try:
        search_term = request.args.get("search_term")

        # Check if we're in local dev mode
        if os.getenv("LOCAL_DEV_MODE") == "true":
            # In local dev mode, return mock accounts
            mock_accounts = [
                {
                    "Id": "1",
                    "Name": "Undeposited Funds",
                    "FullyQualifiedName": "Undeposited Funds",
                    "AccountType": "Other Current Assets",
                    "AccountSubType": "UndepositedFunds",
                },
                {
                    "Id": "2",
                    "Name": "Checking",
                    "FullyQualifiedName": "Checking",
                    "AccountType": "Bank",
                    "AccountSubType": "Checking",
                },
                {
                    "Id": "3",
                    "Name": "Donations",
                    "FullyQualifiedName": "Donations",
                    "AccountType": "Income",
                    "AccountSubType": "NonProfitIncome",
                },
                {
                    "Id": "4",
                    "Name": "Sales",
                    "FullyQualifiedName": "Sales",
                    "AccountType": "Income",
                    "AccountSubType": "SalesOfProductIncome",
                },
            ]

            # Filter mock accounts by search term if provided
            if search_term:
                search_lower = search_term.lower()
                mock_accounts = [
                    acc
                    for acc in mock_accounts
                    if search_lower in acc["Name"].lower()
                    or search_lower in acc["FullyQualifiedName"].lower()
                ]

            return jsonify({"success": True, "data": {"accounts": mock_accounts}})

        # Production mode - use Flask session
        from flask import session as flask_session

        session_id = flask_session.get("app_session_id")
        if not session_id:
            return (
                jsonify({"success": False, "error": "No active session found"}),
                400,
            )

        # Create QuickBooks client and fetch accounts
        from .quickbooks_service import QuickBooksClient

        qb_client = QuickBooksClient(session_id)
        accounts = qb_client.list_accounts(search_term=search_term)

        return jsonify({"success": True, "data": {"accounts": accounts}})

    except QuickBooksError as qbe:
        logger.error(f"QuickBooks API error fetching accounts: {qbe}")
        return (
            jsonify({"success": False, "error": str(qbe), "details": qbe.detail}),
            qbe.status_code,
        )
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}")
        return jsonify({"success": False, "error": "Failed to fetch accounts"}), 500


@app.route("/api/search_accounts", methods=["GET"])
def search_accounts():
    """Search for accounts in QuickBooks."""
    try:
        search_term = request.args.get("search_term")
        if not search_term:
            return jsonify({"success": False, "error": "Missing search_term"}), 400

        # Use the same logic as get_accounts but with search term
        return get_accounts()

    except Exception as e:
        logger.error(f"Error searching accounts: {e}")
        return jsonify({"success": False, "error": "Failed to search accounts"}), 500


@app.route("/api/items", methods=["GET"])
def get_items():
    """
    Get all items (products/services) from QuickBooks.

    Requires X-Session-ID header for QuickBooks authentication (in production).
    Returns list of items with their names and associated income accounts.
    """
    try:
        # Check if we're in local dev mode
        if os.getenv("LOCAL_DEV_MODE") == "true":
            # In local dev mode, return mock items
            mock_items = [
                {
                    "Id": "1",
                    "Name": "General Donation",
                    "FullyQualifiedName": "General Donation",
                    "Type": "Service",
                    "IncomeAccountRef": {"value": "3", "name": "Donations"},
                },
                {
                    "Id": "2",
                    "Name": "Event Sponsorship",
                    "FullyQualifiedName": "Event Sponsorship",
                    "Type": "Service",
                    "IncomeAccountRef": {"value": "3", "name": "Donations"},
                },
            ]
            return jsonify({"success": True, "data": {"items": mock_items}})

        # Production mode - require session ID
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return (
                jsonify({"success": False, "error": "Missing X-Session-ID header"}),
                400,
            )

        # Create QuickBooks client and fetch items
        from .quickbooks_service import QuickBooksClient

        qb_client = QuickBooksClient(session_id)
        items = qb_client.list_items()

        return jsonify({"success": True, "data": {"items": items}})

    except QuickBooksError as qbe:
        logger.error(f"QuickBooks API error fetching items: {qbe}")
        return (
            jsonify({"success": False, "error": str(qbe), "details": qbe.detail}),
            qbe.status_code,
        )
    except Exception as e:
        logger.error(f"Error fetching items: {e}")
        return jsonify({"success": False, "error": "Failed to fetch items"}), 500


@app.route("/api/sales_receipts", methods=["POST"])
@limiter.limit("100 per hour")
def create_sales_receipt():
    """
    Create a sales receipt in QuickBooks.

    Expects JSON data with:
    - donation: The donation data
    - deposit_account_id: ID of the account to deposit to
    - item_id: ID of the item/product (required for sales receipts)

    Requires X-Session-ID header for QuickBooks authentication (in production).
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return (
                jsonify({"success": False, "error": "Missing JSON request body"}),
                400,
            )

        donation = data.get("donation")
        deposit_account_id = data.get("deposit_account_id")
        item_id = data.get("item_id")

        if not donation:
            return (
                jsonify({"success": False, "error": "Missing donation data"}),
                400,
            )

        if not deposit_account_id:
            return (
                jsonify({"success": False, "error": "Missing deposit_account_id"}),
                400,
            )

        if not item_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Must provide item_id for sales receipts",
                    }
                ),
                400,
            )

        # Check if we're in local dev mode
        if os.getenv("LOCAL_DEV_MODE") == "true":
            # In local dev mode, simulate success
            logger.info("Local dev mode: Simulating sales receipt creation")
            mock_receipt = {
                "Id": f"mock-{datetime.now().timestamp()}",
                "TxnDate": donation["payment_info"]["payment_date"],
                "DocNumber": donation["payment_info"]["payment_ref"],
                "TotalAmt": float(donation["payment_info"]["amount"]),
                "CustomerRef": {
                    "value": donation["status"].get("qbo_customer_id", "1"),
                    "name": donation["payer_info"]["customer_ref"]["display_name"],
                },
                "DepositToAccountRef": {
                    "value": deposit_account_id,
                    "name": "Undeposited Funds",
                },
            }
            return jsonify({"success": True, "data": {"sales_receipt": mock_receipt}})

        # Production mode - require session ID
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return (
                jsonify({"success": False, "error": "Missing X-Session-ID header"}),
                400,
            )

        # Create QuickBooks client
        from .quickbooks_service import QuickBooksClient

        qb_client = QuickBooksClient(session_id)

        # Extract needed fields
        payment_ref = donation["payment_info"]["payment_ref"]
        payment_date = donation["payment_info"]["payment_date"]
        amount = donation["payment_info"]["amount"]

        # Get last name from customer_ref
        last_name = donation["payer_info"]["customer_ref"].get("last_name", "")

        # Format the sales receipt number as {DATE}_{Payment Ref}
        # Convert date from YYYY-MM-DD to YYYYMMDD format
        date_formatted = payment_date.replace("-", "")
        sales_receipt_number = f"{date_formatted}_{payment_ref}"

        # Check if customer ID exists (required for sales receipts)
        customer_id = donation["status"].get("qbo_customer_id")
        if not customer_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Customer must be created in QuickBooks before "
                        "creating sales receipt",
                    }
                ),
                400,
            )

        # Format description as Payment_REf_LastName_Date_Amount
        # Ensure amount is formatted with 2 decimal places
        amount_float = float(amount)
        amount_formatted = f"{amount_float:.2f}"
        description = f"{payment_ref}_{last_name}_{payment_date}_{amount_formatted}"

        # Build sales receipt data
        sales_receipt_data = {
            "CustomerRef": {"value": customer_id},  # Use the validated customer ID
            "TxnDate": payment_date,
            "DocNumber": sales_receipt_number,
            "PrivateNote": donation["payment_info"]["memo"],
            "DepositToAccountRef": {"value": deposit_account_id},
        }

        # Set payment method based on deposit method or payment method
        deposit_method = donation["payment_info"].get("deposit_method")

        # Also check raw donation data if available
        raw_payment_method = ""
        if "_match_data" in donation:
            # Try to get from match data's raw donation
            raw_donation = donation.get("_match_data", {})
            if isinstance(raw_donation, dict) and "PaymentInfo" in raw_donation:
                raw_payment_method = raw_donation.get("PaymentInfo", {}).get(
                    "Payment_Method", ""
                )

        # Log for debugging
        logger.info(
            f"Payment method detection - deposit_method: {deposit_method}, "
            f"raw_payment_method: {raw_payment_method}, "
            f"payment_ref: {payment_ref}"
        )

        # Check both deposit_method and payment_method fields
        # Also assume numeric payment refs are likely checks
        is_check = (
            (deposit_method and "check" in deposit_method.lower())
            or (raw_payment_method and "check" in raw_payment_method.lower())
            or (
                payment_ref and payment_ref.isdigit() and len(payment_ref) <= 6
            )  # Check number pattern
        )

        if is_check:
            # Query available payment methods to find "Check"
            try:
                payment_methods = qb_client.list_payment_methods()
                check_method = None

                # Look for payment method named "Check" (case-insensitive)
                for pm in payment_methods:
                    if pm.get("Name", "").lower() == "check":
                        check_method = pm
                        break

                if check_method:
                    # Use the ID from QuickBooks
                    sales_receipt_data["PaymentMethodRef"] = {
                        "value": check_method["Id"]
                    }
                    logger.info(
                        f"Found Check payment method with ID: {check_method['Id']}"
                    )
                else:
                    logger.warning("Check payment method not found in QuickBooks")
                    # Try using "Check" as the value directly as a fallback
                    sales_receipt_data["PaymentMethodRef"] = {
                        "value": "1"
                    }  # Default Check ID
                    logger.info("Using default Check payment method ID: 1")
            except Exception as e:
                logger.error(f"Error fetching payment methods: {e}")
                # Try using "Check" as the value directly as a fallback
                sales_receipt_data["PaymentMethodRef"] = {
                    "value": "1"
                }  # Default Check ID
                logger.info("Using default Check payment method ID: 1 due to error")

        # For sales receipts, the reference number goes in PaymentRefNum field
        sales_receipt_data["PaymentRefNum"] = payment_ref

        # Build line item
        if item_id:
            # Using item/product
            line_item = {
                "Amount": float(amount),
                "DetailType": "SalesItemLineDetail",
                "SalesItemLineDetail": {
                    "ItemRef": {"value": item_id},
                    "Qty": 1,  # Set quantity to 1
                },
                "Description": description,  # Add the formatted description
                # Note: ServiceDate is not supported on sales receipts, only on invoices
            }
        else:
            # QuickBooks sales receipts require an item, not just an income account
            # Return error if no item is provided
            return (
                jsonify(
                    {
                        "success": False,
                        "error": (
                            "Sales receipts require an item. Please select a "
                            "product or service item, not just an income account."
                        ),
                    }
                ),
                400,
            )

        sales_receipt_data["Line"] = [line_item]

        # Log the payload for debugging
        logger.info(
            f"Sales receipt payload: {json.dumps(sales_receipt_data, indent=2)}"
        )

        # Create the sales receipt
        sales_receipt = qb_client.create_sales_receipt(sales_receipt_data)

        return jsonify({"success": True, "data": {"sales_receipt": sales_receipt}})

    except QuickBooksError as qbe:
        logger.error(f"QuickBooks API error creating sales receipt: {qbe}")
        return (
            jsonify({"success": False, "error": str(qbe), "details": qbe.detail}),
            qbe.status_code,
        )
    except Exception as e:
        logger.error(f"Error creating sales receipt: {e}")
        return (
            jsonify({"success": False, "error": "Failed to create sales receipt"}),
            500,
        )


@app.route("/api/customers", methods=["POST"])
def create_customer_endpoint():
    """
    Create a new customer in QuickBooks.

    Expects JSON data with customer information.
    Requires X-Session-ID header for QuickBooks authentication (in production).
    """
    try:
        # Get JSON data from request body
        data = request.get_json()
        if not data:
            return (
                jsonify({"success": False, "error": "Missing JSON request body"}),
                400,
            )

        # Import the customer data source factory
        from .customer_data_source import create_customer_data_source

        # Check if we're in local dev mode
        if os.getenv("LOCAL_DEV_MODE") == "true":
            # In local dev mode, use CSV data source
            from pathlib import Path

            csv_path = (
                Path(__file__).parent.parent
                / "src/tests/test_files/customer_contact_list.csv"
            )
            if not csv_path.exists():
                return (
                    jsonify(
                        {"success": False, "error": f"CSV file not found at {csv_path}"}
                    ),
                    500,
                )

            logger.info(f"Local dev mode: Creating customer in CSV file at {csv_path}")
            data_source = create_customer_data_source(csv_path=csv_path)
        else:
            # Production mode - require session ID
            session_id = request.headers.get("X-Session-ID")
            if not session_id:
                return (
                    jsonify({"success": False, "error": "Missing X-Session-ID header"}),
                    400,
                )

            logger.info("Production mode: Creating customer via QuickBooks API")
            data_source = create_customer_data_source(session_id=session_id)

        # Create the customer using the appropriate data source
        new_customer = data_source.create_customer(customer_data=data)

        return jsonify({"success": True, "data": new_customer})

    except QuickBooksError as qbe:
        logger.error(f"QuickBooks API error: {qbe}")
        return (
            jsonify({"success": False, "error": str(qbe), "details": qbe.detail}),
            500,
        )
    except Exception as e:
        logger.error(f"Error creating customer: {e}")
        return jsonify({"success": False, "error": "Failed to create customer"}), 500


# Specific route for auth callback
@app.route("/auth/callback")
def auth_callback():
    """Serve React app for OAuth callback."""
    if app.static_folder and os.path.exists(app.static_folder):
        response = make_response(app.send_static_file("index.html"))
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    else:
        return jsonify({"error": "React app not found"}), 404


# Route to serve markdown files (EULA and Privacy Policy)
@app.route("/EULA.md")
def serve_eula():
    """Serve the EULA markdown file."""
    try:
        eula_path = os.path.join(os.path.dirname(__file__), "..", "EULA.md")
        with open(eula_path, "r") as f:
            content = f.read()
        response = make_response(content)
        response.headers["Content-Type"] = "text/markdown; charset=utf-8"
        return response
    except FileNotFoundError:
        return jsonify({"error": "EULA not found"}), 404


@app.route("/PRIVACY_POLICY.md")
def serve_privacy_policy():
    """Serve the Privacy Policy markdown file."""
    try:
        privacy_path = os.path.join(
            os.path.dirname(__file__), "..", "PRIVACY_POLICY.md"
        )
        with open(privacy_path, "r") as f:
            content = f.read()
        response = make_response(content)
        response.headers["Content-Type"] = "text/markdown; charset=utf-8"
        return response
    except FileNotFoundError:
        return jsonify({"error": "Privacy Policy not found"}), 404


# Catch-all route for React client-side routing
# This must be at the end to avoid catching API routes
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react_app(path):
    """Serve React app for client-side routing."""
    logger.info(f"Catch-all route hit with path: {path}")

    # Check if we have a static folder (production mode)
    if app.static_folder and os.path.exists(app.static_folder):
        # Check if it's an API route that wasn't matched
        if path.startswith("api/"):
            return jsonify({"error": "API endpoint not found"}), 404

        # For paths that don't have a file extension, serve index.html
        # This handles React routes like /auth/callback
        if not path or "." not in path:
            logger.info(f"Serving index.html for path: {path}")
            response = make_response(app.send_static_file("index.html"))
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response

        # Try to serve the exact file if it exists
        try:
            response = make_response(app.send_static_file(path))
            # Add cache control headers for all static files
            if path.endswith((".js", ".css")):
                response.headers[
                    "Cache-Control"
                ] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            return response
        except Exception:
            # If file doesn't exist, serve index.html for React routing
            logger.info(f"File not found, serving index.html for path: {path}")
            response = make_response(app.send_static_file("index.html"))
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
    else:
        # In development mode
        return jsonify(
            {
                "message": "Development mode - React app runs on http://localhost:3000",
                "api": "http://localhost:5000/api/",
            }
        )


@app.errorhandler(413)
def request_entity_too_large(e):
    """Handle file size exceeded error."""
    return (
        jsonify(
            {
                "success": False,
                "error": (
                    f"File too large. Maximum size is "
                    f"{Config.MAX_FILE_SIZE_MB}MB per file"
                ),
            }
        ),
        413,
    )


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    return e


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {e}")
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Internal server error"}), 500
    return e


if __name__ == "__main__":
    app.run(debug=True)
