"""Flask application with donation processing API endpoints."""
import glob
import logging
import os
from contextlib import suppress

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from .config import Config, session_backend, storage_backend
from .donation_processor import process_donation_documents
from .quickbooks_auth import qbo_auth
from .storage import S3Storage

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Flask app
if os.environ.get("NODE_ENV") == "production":
    # In production, serve static files from React build
    static_folder = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
    )
    app = Flask(__name__, static_folder=static_folder, static_url_path="")
else:
    # In development, use default static folder
    app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = (
    Config.MAX_FILE_SIZE_BYTES * Config.MAX_FILES_PER_UPLOAD
)

# Enable CORS for all routes with specific configuration
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:5000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Session-ID"],
            "supports_credentials": True,
        }
    },
)


@app.route("/api/")
def hello():
    """Return API information."""
    return jsonify(
        {
            "name": "QuickBooks Donation Manager API",
            "version": "1.0.0",
            "endpoints": {
                "/api/upload": "POST - Upload donation documents",
                "/api/process": "POST - Process uploaded documents",
                "/api/health": "GET - Health check",
                "/api/auth/qbo/authorize": "GET - Get OAuth2 authorization URL",
                "/api/auth/qbo/callback": "GET - Handle OAuth2 callback",
                "/api/auth/qbo/refresh": "POST - Refresh access token",
                "/api/auth/qbo/revoke": "POST - Revoke tokens",
                "/api/auth/qbo/status": "GET - Check authentication status",
            },
        }
    )


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "storage": type(storage_backend).__name__,
            "session": type(session_backend).__name__,
        }
    )


# QuickBooks OAuth2 endpoints
@app.route("/api/auth/qbo/authorize", methods=["GET"])
def qbo_authorize():
    """
    Generate QuickBooks OAuth2 authorization URL.

    Returns:
        JSON with authorization URL and state
    """
    try:
        if qbo_auth is None:
            return jsonify({"success": False, "error": "OAuth2 not configured"}), 500

        # Get session ID from request or generate new one
        session_id = request.headers.get("X-Session-ID", Config.generate_upload_id())

        # Generate authorization URL
        auth_url, state = qbo_auth.get_authorization_url(session_id)

        logger.info(f"Generated auth URL: {auth_url}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"State: {state}")

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

        logger.info(
            f"OAuth2 callback received - code: {code[:10]}..., "
            f"state: {state}, realmId: {realm_id}"
        )

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
        logger.info(f"Session ID from header: {session_id}")

        # Exchange code for tokens (session_id can be extracted from state)
        result = qbo_auth.exchange_authorization_code(
            code=code, realm_id=realm_id, state=state, session_id=session_id
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

        return jsonify({"success": True, "data": result})

    except ValueError as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({"success": False, "error": "Failed to refresh token"}), 500


@app.route("/api/auth/qbo/revoke", methods=["POST"])
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

    Requires:
        X-Session-ID header
    """
    try:
        # Get session ID from header
        session_id = request.headers.get("X-Session-ID")
        if not session_id:
            return jsonify({"success": True, "data": {"authenticated": False}})

        # Get auth status
        status = qbo_auth.get_auth_status(session_id)

        return jsonify({"success": True, "data": status})

    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({"success": True, "data": {"authenticated": False}})


@app.route("/api/debug/build", methods=["GET"])
def debug_build():
    """Debug endpoint to check build directory contents."""
    build_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
    )

    result = {"build_dir": build_dir, "exists": os.path.exists(build_dir), "files": []}

    if os.path.exists(build_dir):
        all_files = glob.glob(os.path.join(build_dir, "**/*"), recursive=True)
        for file_path in all_files:
            if os.path.isfile(file_path):
                relative_path = os.path.relpath(file_path, build_dir)
                result["files"].append(relative_path)

    return jsonify(result)


@app.route("/api/upload", methods=["POST"])
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
    Process uploaded donation documents.

    Expects JSON with upload_id.
    Runs Gemini extraction, validation, and deduplication.

    Returns:
        JSON response with processed donations and metadata
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
                    },
                }
            )

        # Get file paths based on storage backend
        if isinstance(storage_backend, S3Storage):
            # For S3, download files to temp directory
            temp_paths = storage_backend.download_batch_to_temp(upload_id)
            file_paths = [str(p) for p in temp_paths]
        else:
            # For local storage, use paths directly
            file_paths = storage_backend.get_file_paths(upload_id)

        # Process the documents
        try:
            logger.info(f"Processing {len(file_paths)} files for upload {upload_id}")

            # Run extraction, validation, and deduplication
            processed_donations, extraction_metadata = process_donation_documents(
                file_paths
            )

            # Calculate metadata
            processing_metadata = {
                "files_processed": len(file_paths),
                "valid_count": extraction_metadata["valid_count"],
                "raw_count": extraction_metadata["raw_count"],
                "duplicate_count": extraction_metadata["duplicate_count"],
            }

            # Update session with results
            session_backend.update_upload_metadata(
                upload_id,
                {
                    "status": "processed",
                    "donations": processed_donations,
                    "processing_metadata": processing_metadata,
                },
            )

            # Clean up temp files if using S3
            if isinstance(storage_backend, S3Storage):
                for temp_path in temp_paths:
                    with suppress(Exception):
                        temp_path.unlink()

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "donations": processed_donations,
                        "metadata": processing_metadata,
                    },
                }
            )

        except Exception as e:
            logger.error(f"Processing error: {e}")

            # Clean up temp files if using S3
            if isinstance(storage_backend, S3Storage) and "temp_paths" in locals():
                for temp_path in temp_paths:
                    with suppress(Exception):
                        temp_path.unlink()

            # Update status
            session_backend.update_upload_metadata(
                upload_id, {"status": "failed", "error": str(e)}
            )

            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Failed to process documents: {str(e)}",
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Process endpoint error: {e}")
        return (
            jsonify({"success": False, "error": "An error occurred during processing"}),
            500,
        )


# Catch-all route for React client-side routing
# This must be at the end to avoid catching API routes
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react_app(path):
    """Serve React app for client-side routing."""
    # In production, serve the React app for non-API routes
    if os.environ.get("NODE_ENV") == "production" or os.environ.get("DYNO"):
        # Check if it's an API route that wasn't matched
        if path.startswith("api/"):
            return jsonify({"error": "API endpoint not found"}), 404

        # Check if path is a static file
        static_file_path = os.path.join(app.static_folder, path)
        if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
            return app.send_static_file(path)

        # For everything else (including /auth/callback), serve index.html
        return app.send_static_file("index.html")
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


if __name__ == "__main__":
    app.run(debug=True)
