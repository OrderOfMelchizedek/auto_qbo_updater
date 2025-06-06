"""Flask application with donation processing API endpoints."""
import glob
import logging
import os
from contextlib import suppress

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from .config import Config, session_backend, storage_backend
from .donation_processor import process_donation_documents
from .storage import S3Storage

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = (
    Config.MAX_FILE_SIZE_BYTES * Config.MAX_FILES_PER_UPLOAD
)

# Enable CORS for all routes
CORS(app)


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


# Serve React app for production
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react_app(path):
    """Serve React app in production."""
    # Skip API routes
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404

    # Check if we're in production (Heroku sets NODE_ENV)
    if os.environ.get("NODE_ENV") == "production":
        # Get the absolute path to the build directory
        build_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
        )

        if not os.path.exists(build_dir):
            return jsonify({"error": "React build not found"}), 500

        # For static files, serve them directly
        if path and not path.endswith("/"):
            static_file = os.path.join(build_dir, path)
            if os.path.isfile(static_file):
                return send_from_directory(build_dir, path)

        # For everything else (including root), serve index.html
        return send_from_directory(build_dir, "index.html")
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
