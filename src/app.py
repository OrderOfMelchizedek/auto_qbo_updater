"""Main Flask application for FOM to QBO automation."""

import os
import sys

# Debug: Print Python path and environment info
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"__file__: {__file__}")
print(f"DYNO env var (Heroku indicator): {os.environ.get('DYNO', 'Not on Heroku')}")

# Load environment variables immediately
from dotenv import load_dotenv

load_dotenv()

# Debug: Check if .env file exists
if os.path.exists(".env"):
    print(".env file found")
else:
    print(".env file NOT found")

import argparse
import json
import mimetypes
import re
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import quote

import dateutil.parser
import pandas as pd
import redis
import requests
from dotenv import load_dotenv
from flask import Flask, Response, flash, jsonify, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename

# Try importing from the src package first
from utils.exceptions import (
    FileProcessingException,
    FOMQBOException,
    GeminiAPIException,
    QBOAPIException,
    ValidationException,
)
from utils.file_processor import FileProcessor
from utils.gemini_service import GeminiService
from utils.memory_monitor import memory_monitor
from utils.progress_logger import init_progress_logger, log_progress, progress_logger
from utils.qbo_service import QBOService

try:
    import magic  # python-magic for file content validation
except ImportError:
    # On macOS, might need python-magic-bin
    magic = None

# Load environment variables
load_dotenv()

# Configure logging
import logging
import sys
from logging.handlers import RotatingFileHandler

from services.deduplication import DeduplicationService

# Import from new modular services
from services.validation import (
    log_audit_event,
    normalize_amount,
    normalize_check_number,
    normalize_date,
    normalize_donor_name,
    sanitize_for_logging,
    validate_donation_date,
    validate_environment,
)


def configure_logging():
    """Configure comprehensive logging for development and production."""
    # Determine log level based on environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    is_production = os.getenv("FLASK_ENV", "development") == "production"

    # Create logs directory if it doesn't exist
    try:
        os.makedirs("logs", exist_ok=True)
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
    if os.path.exists("logs") or not is_production:
        try:
            # General application log
            app_handler = RotatingFileHandler(
                "logs/fom_qbo.log", maxBytes=10485760, backupCount=5, encoding="utf-8"  # 10MB
            )
            app_handler.setLevel(logging.INFO)
            app_handler.setFormatter(detailed_format)
            root_logger.addHandler(app_handler)

            # Error-only log for monitoring
            error_handler = RotatingFileHandler(
                "logs/errors.log", maxBytes=5242880, backupCount=3, encoding="utf-8"  # 5MB
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(detailed_format)
            root_logger.addHandler(error_handler)

            # Audit log for security events
            audit_handler = RotatingFileHandler(
                "logs/audit.log", maxBytes=5242880, backupCount=10, encoding="utf-8"  # 5MB
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

    return logging.getLogger(__name__)


# Initialize logging
logger = configure_logging()
audit_logger = logging.getLogger("audit")


def process_single_file(file_data, qbo_authenticated):
    """Process a single file for donation extraction.

    Args:
        file_data: Dictionary containing file information
        qbo_authenticated: Whether QBO is authenticated

    Returns:
        Dictionary with processing results
    """
    result = {
        "success": False,
        "filename": file_data["filename"],
        "error": None,
        "donations": [],
        "file_path": None,
        "processing_time": 0,
    }

    import time

    start_time = time.time()

    try:
        file_storage = file_data["file_storage"]
        original_filename = file_data["filename"]

        # Validate file extension
        _, ext = os.path.splitext(original_filename)
        ext = ext.lower()

        if ext not in ALLOWED_EXTENSIONS:
            result["error"] = f"File type not allowed: {original_filename}"
            return result

        # Check file size
        file_storage.seek(0, os.SEEK_END)
        file_size = file_storage.tell()
        file_storage.seek(0)

        if file_size > MAX_FILE_SIZE:
            result["error"] = f"File too large: {original_filename} ({file_size / 1024 / 1024:.1f}MB)"
            return result

        # Generate secure filename and save
        secure_name = generate_secure_filename(original_filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_name)

        file_storage.save(file_path)
        result["file_path"] = file_path

        # Validate file content
        with open(file_path, "rb") as f:
            file_content = f.read()

        is_valid = validate_file_content(file_content, original_filename)
        if not is_valid:
            result["error"] = f"Invalid file content: {original_filename}"
            cleanup_uploaded_file(file_path)
            return result

        # Process the file
        log_progress(f"Processing {original_filename} in parallel...")
        extracted_data = file_processor.process(file_path, ext)

        if extracted_data:
            if isinstance(extracted_data, list):
                result["donations"] = extracted_data
            else:
                result["donations"] = [extracted_data]

            # Apply customer matching if QBO is authenticated
            if qbo_authenticated and result["donations"]:
                # Get QBO service instance from app context
                from flask import current_app

                qbo_service = current_app.qbo_service

                for donation in result["donations"]:
                    if donation.get("Donor Name"):
                        customer = qbo_service.find_customer(donation["Donor Name"])
                        if customer:
                            donation["qboCustomerId"] = customer.get("Id")
                            donation["qbCustomerStatus"] = "Found"
                            donation["matchMethod"] = "Automatic"
                            donation["matchConfidence"] = "High"
                        else:
                            donation["qbCustomerStatus"] = "New"
            else:
                # If not authenticated, mark all donations as needing customer creation
                for donation in result["donations"]:
                    if "qbCustomerStatus" not in donation:
                        donation["qbCustomerStatus"] = "New"

            result["success"] = True
            log_progress(f"Successfully processed {original_filename}: {len(result['donations'])} donations found")
        else:
            result["error"] = f"No donation data extracted from {original_filename}"

    except Exception as e:
        result["error"] = f"Error processing {original_filename}: {str(e)}"
        logger.error(f"Error in process_single_file: {e}", exc_info=True)

    finally:
        result["processing_time"] = time.time() - start_time

    return result


# File upload security configuration
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf", ".csv"}
ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "application/pdf": [".pdf"],
    "text/csv": [".csv"],
    "text/plain": [".csv"],  # Some CSV files are detected as text/plain
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file

# Date validation configuration
# Donations older than this many days are flagged as potentially incorrect
DATE_WARNING_DAYS = int(os.getenv("DATE_WARNING_DAYS", "365"))  # Default: 1 year
# Donations with future dates more than this many days are rejected
FUTURE_DATE_LIMIT_DAYS = int(os.getenv("FUTURE_DATE_LIMIT_DAYS", "7"))  # Default: 1 week


def generate_secure_filename(original_filename):
    """Generate a secure filename with UUID to prevent conflicts and path traversal."""
    # Get file extension
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower()

    # Generate unique filename
    unique_id = str(uuid.uuid4())
    secure_name = f"{unique_id}{ext}"

    return secure_name


def validate_file_content(file_path):
    """Validate file content matches its extension using python-magic."""
    try:
        # Get file extension
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        if magic is None:
            # Fallback: just check extension is allowed
            if ext in ALLOWED_EXTENSIONS:
                return True, None
            else:
                return False, f"File extension {ext} is not allowed"

        # Get MIME type from file content
        mime = magic.Magic(mime=True)
        detected_type = mime.from_file(file_path)

        # Check if MIME type is allowed and matches extension
        if detected_type in ALLOWED_MIME_TYPES:
            allowed_exts = ALLOWED_MIME_TYPES[detected_type]
            if ext in allowed_exts:
                return True, None
            else:
                return False, f"File extension {ext} doesn't match content type {detected_type}"
        else:
            return False, f"File type {detected_type} is not allowed"

    except Exception as e:
        return False, f"Error validating file: {str(e)}"


def cleanup_uploaded_file(file_path):
    """Safely remove uploaded file and trigger garbage collection."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up file: {file_path}")
            # Force garbage collection after file cleanup
            import gc

            gc.collect()
    except Exception as e:
        print(f"Error cleaning up file {file_path}: {str(e)}")


# Note: Environment validation moved to create_app() to ensure it runs after gunicorn initialization


# Define model aliases
MODEL_MAPPING = {
    "gemini-flash": "gemini-2.5-flash-preview-04-17",
    "gemini-pro": "gemini-2.5-pro-preview-03-25",
    # Include the full model names as keys for consistency
    "gemini-2.5-flash-preview-04-17": "gemini-2.5-flash-preview-04-17",
    "gemini-2.5-pro-preview-03-25": "gemini-2.5-pro-preview-03-25",
}

# Resolve the environment variable model
gemini_env_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-preview-04-17")
# If the environment variable is an alias, resolve it
resolved_env_model = MODEL_MAPPING.get(gemini_env_model, gemini_env_model)

# Parse command line arguments for QBO environment and Gemini model
parser = argparse.ArgumentParser(description="FOM to QBO Automation App")
parser.add_argument(
    "--env",
    type=str,
    choices=["sandbox", "production"],
    default=os.getenv("QBO_ENVIRONMENT", "sandbox"),
    help="QuickBooks Online environment (sandbox or production)",
)
parser.add_argument(
    "--model",
    type=str,
    default=resolved_env_model,
    choices=[
        "gemini-flash",
        "gemini-pro",
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.5-pro-preview-03-25",
    ],
    help="Gemini model to use (flash for faster responses, pro for better quality)",
)
args, _ = parser.parse_known_args()

# Use the command-line specified environment
qbo_environment = args.env
# Resolve model alias if needed
gemini_model = MODEL_MAPPING.get(args.model, args.model)

print(f"Starting application with QBO environment: {qbo_environment}")
print(f"Using Gemini model: {gemini_model}")

app = Flask(__name__)

# Track application start time for uptime monitoring
import time

app.start_time = time.time()

# Environment variables are already loaded at the top of the file

# Debug: Print environment variables (sanitized)
print("Environment variables check:")
for var in ["FLASK_SECRET_KEY", "GEMINI_API_KEY", "QBO_CLIENT_ID", "QBO_CLIENT_SECRET", "QBO_REDIRECT_URI"]:
    value = os.environ.get(var)
    if value:
        # Print first 4 chars only for security
        print(f"  {var}: {'*' * 4}{value[:4]}...{value[-4:]}")
    else:
        print(f"  {var}: NOT SET")

# Validate environment variables after Flask initialization
# This ensures gunicorn has fully loaded the environment
try:
    validate_environment()
except ValueError as e:
    print(f"Environment validation failed: {e}")
    # On Heroku, sometimes env vars take a moment to be available
    # Let's check if we're on Heroku and give it another try
    if os.environ.get("DYNO"):
        print("Detected Heroku environment, retrying environment check...")
        import time

        time.sleep(2)  # Give Heroku a moment
        validate_environment()
    else:
        raise

# Set Flask secret key from environment variable (already validated)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB upload limit

# Initialize CSRF protection
csrf = CSRFProtect(app)
# Configure CSRF to accept tokens in X-CSRFToken header (for AJAX requests)
app.config["WTF_CSRF_HEADERS"] = ["X-CSRFToken"]

# Initialize rate limiter
# For now, disable rate limiting in production due to Redis SSL issues
# TODO: Fix Redis SSL configuration for Flask-Limiter
redis_url = os.environ.get("REDIS_URL")
if redis_url:
    # Use memory storage for rate limiting until Redis SSL is fixed
    print("Using memory storage for rate limiting (Redis SSL issue workaround)")
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri="memory://",
    )
else:
    # Use memory storage for development
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri="memory://",
    )


# Configure server-side session storage
def configure_session(app):
    """Configure server-side session storage with Redis or filesystem fallback."""
    redis_url = os.environ.get("REDIS_URL")

    if redis_url:
        # Use Redis for production
        try:
            # Parse Redis URL (handles various formats including Heroku's)
            if redis_url.startswith(("redis://", "rediss://")):
                app.config["SESSION_TYPE"] = "redis"
                # Handle Heroku Redis SSL URLs
                if redis_url.startswith("rediss://"):
                    # For SSL Redis connections, we need special handling
                    app.config["SESSION_REDIS"] = redis.from_url(redis_url, ssl_cert_reqs=None)
                else:
                    app.config["SESSION_REDIS"] = redis.from_url(redis_url)
                print("Using Redis for session storage")
            else:
                raise ValueError("Invalid REDIS_URL format")
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            print("Falling back to filesystem session storage")
            configure_filesystem_sessions(app)
    else:
        # Use filesystem for development
        print("No REDIS_URL found. Using filesystem for session storage (development mode)")
        configure_filesystem_sessions(app)

    # Common session configuration
    app.config["SESSION_PERMANENT"] = False
    app.config["SESSION_USE_SIGNER"] = True
    app.config["SESSION_KEY_PREFIX"] = "fom_qbo:"
    app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour

    # Initialize Flask-Session
    Session(app)


def configure_filesystem_sessions(app):
    """Configure filesystem-based sessions for development."""
    session_dir = os.path.join(tempfile.gettempdir(), "fom_qbo_sessions")
    os.makedirs(session_dir, exist_ok=True)
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = session_dir
    app.config["SESSION_FILE_THRESHOLD"] = 100  # Max number of sessions


# Configure session storage
configure_session(app)

# Create necessary directories
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize Redis client for QBO token persistence
redis_client = None
redis_url = os.environ.get("REDIS_URL")
if redis_url:
    try:
        if redis_url.startswith("rediss://"):
            # SSL Redis connection
            redis_client = redis.from_url(redis_url, ssl_cert_reqs=None)
        else:
            redis_client = redis.from_url(redis_url)
        # Test connection
        redis_client.ping()
        logger.info("Redis connection established for QBO token persistence")
    except Exception as e:
        logger.error(f"Failed to connect to Redis for token persistence: {e}")
        redis_client = None

# Initialize services
gemini_service = GeminiService(
    api_key=os.getenv("GEMINI_API_KEY"),
    model_name=gemini_model,  # Use the command-line specified model
)
qbo_service = QBOService(
    client_id=os.getenv("QBO_CLIENT_ID"),
    client_secret=os.getenv("QBO_CLIENT_SECRET"),
    redirect_uri=os.getenv("QBO_REDIRECT_URI"),
    environment=qbo_environment,  # Use the command-line specified environment
    redis_client=redis_client,  # Pass Redis client for token persistence
)
# Pass both services to the file processor for integrated customer matching
file_processor = FileProcessor(gemini_service, qbo_service, progress_logger)

# Initialize progress logger with Gemini service
init_progress_logger(gemini_service)

# Add services to app context so blueprints can access them
app.qbo_service = qbo_service
app.file_processor = file_processor
app.memory_monitor = memory_monitor
app.process_single_file = process_single_file
app.cleanup_uploaded_file = cleanup_uploaded_file

# Import and register blueprints
from routes import auth_bp, donations_bp, files_bp, health_bp, qbo_bp

app.register_blueprint(health_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(files_bp)
app.register_blueprint(donations_bp)
app.register_blueprint(qbo_bp)


# Routes
@app.route("/")
def index():
    """Render the main application page."""
    return render_template("index.html")


@app.route("/save", methods=["POST"])
def save_changes():
    """Save current donation data to session."""
    try:
        data = request.json

        if data and "donations" in data:
            session["donations"] = data["donations"]
            session.modified = True

            # Log the save event
            log_audit_event(
                "donations_saved",
                user_id=session.get("session_id"),
                details={"donation_count": len(data["donations"])},
                request_ip=request.remote_addr,
            )

            return jsonify({"success": True})

        return jsonify({"success": False, "message": "No donation data provided"}), 400

    except Exception as e:
        logger.error(f"Error saving donations: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/report/generate", methods=["GET"])
def generate_report():
    """Generate a donation report."""
    try:
        donations = session.get("donations", [])

        if not donations:
            return jsonify({"success": False, "message": "No donations to report"}), 400

        # Format report similar to the provided examples
        report_data = []
        valid_entry_index = 1

        # Current date for the report
        import pandas as pd

        current_date = pd.Timestamp.now().strftime("%m/%d/%Y")

        for donation in donations:
            # Skip entries with missing or invalid gift amounts
            if "Gift Amount" not in donation or not donation["Gift Amount"]:
                logger.info(f"Skipping donation with missing Gift Amount: {donation.get('Donor Name', 'Unknown')}")
                continue

            # Skip entries marked as invalid
            if donation.get("isInvalid", False):
                logger.info(f"Skipping invalid donation: {donation.get('Donor Name', 'Unknown')}")
                continue

            try:
                # Format the amount
                amount = float(str(donation["Gift Amount"]).replace("$", "").replace(",", ""))

                # Format the entry
                report_entry = {
                    "Entry": str(valid_entry_index),
                    "Check #": donation.get("Check # (if applicable)", ""),
                    "Donor Name": donation.get("Donor Name", ""),
                    "Gift Amount": f"${amount:.2f}",
                    "Notes": donation.get("Notes", ""),
                    "Fund": donation.get("Fund", ""),
                    "Gift Date": donation.get("Gift Date", ""),
                    "Gift Type": donation.get("Gift Type", ""),
                    "On Behalf Of": donation.get("On Behalf Of", ""),
                    "QB Customer ID": donation.get("qboCustomerId", ""),
                    "QB Customer Status": donation.get("qbCustomerStatus", "Not Matched"),
                }

                report_data.append(report_entry)
                valid_entry_index += 1

            except (ValueError, TypeError) as e:
                logger.error(f"Error processing donation amount: {e}")
                continue

        # Calculate total amount
        total_amount = sum(float(d["Gift Amount"].replace("$", "").replace(",", "")) for d in report_data)

        # Format entries for frontend expectations
        formatted_entries = []
        for idx, entry in enumerate(report_data, 1):
            donation = next((d for d in donations if d.get("Donor Name") == entry["Donor Name"]), {})
            formatted_entry = {
                "index": idx,
                "donor_name": entry["Donor Name"],
                "address": f"{donation.get('Address - Line 1', '')} {donation.get('City', '')} {donation.get('State', '')} {donation.get('ZIP', '')}".strip(),
                "amount": float(entry["Gift Amount"].replace("$", "").replace(",", "")),
                "date": entry["Gift Date"],
                "check_no": entry["Check #"],
                "memo": donation.get("Memo", ""),
                # Additional fields for CSV export
                "first_name": donation.get("First Name", ""),
                "last_name": donation.get("Last Name", ""),
                "full_name": donation.get("Full Name", ""),
                "organization_name": donation.get("Organization Name", ""),
                "address_line_1": donation.get("Address - Line 1", ""),
                "city": donation.get("City", ""),
                "state": donation.get("State", ""),
                "zip": donation.get("ZIP", ""),
                "deposit_date": donation.get("Deposit Date", ""),
                "deposit_method": donation.get("Deposit Method", ""),
                "customer_lookup": donation.get("customerLookup", ""),
            }
            formatted_entries.append(formatted_entry)

        # Create the report structure matching frontend expectations
        report = {
            "success": True,
            "report": {
                "total": total_amount,
                "entries": formatted_entries,
            },
        }

        return jsonify(report)

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return jsonify({"error": str(e)}), 500


# All other routes have been moved to blueprints in the routes module

if __name__ == "__main__":
    # Display the environment when starting
    print(f"====== Starting with QuickBooks Online {qbo_environment.upper()} environment ======")
    print(f"API Base URL: {qbo_service.api_base}")
    print(f"To change environments, restart with: python src/app.py --env [sandbox|production]")
    print("================================================================")

    # Use debug mode only in development
    debug_mode = os.getenv("FLASK_ENV", "development") == "development"
    app.run(debug=debug_mode)
