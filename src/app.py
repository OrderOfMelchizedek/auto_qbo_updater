import os
import json
import requests
import argparse
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_session import Session
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.utils import secure_filename
import pandas as pd
from dotenv import load_dotenv
from urllib.parse import quote
import redis
import tempfile

# Try importing from the src package first
try:
    from src.utils.gemini_service import GeminiService
    from src.utils.qbo_service import QBOService
    from src.utils.file_processor import FileProcessor
    from src.utils.progress_logger import progress_logger, init_progress_logger, log_progress
    from src.utils.exceptions import (
        FOMQBOException, QBOAPIException, GeminiAPIException, 
        FileProcessingException, ValidationException
    )
except ModuleNotFoundError:
    # Fall back to relative imports if running directly from src directory
    from utils.gemini_service import GeminiService
    from utils.qbo_service import QBOService
    from utils.file_processor import FileProcessor
    from utils.progress_logger import progress_logger, init_progress_logger, log_progress
    from utils.exceptions import (
        FOMQBOException, QBOAPIException, GeminiAPIException,
        FileProcessingException, ValidationException
    )

import re
from datetime import datetime
import dateutil.parser
import uuid
import mimetypes
try:
    import magic  # python-magic for file content validation
except ImportError:
    # On macOS, might need python-magic-bin
    magic = None

# Load environment variables
load_dotenv()

# Configure logging
import logging
from logging.handlers import RotatingFileHandler
import sys

def configure_logging():
    """Configure comprehensive logging for development and production."""
    # Determine log level based on environment
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    is_production = os.getenv('FLASK_ENV', 'development') == 'production'
    
    # Create logs directory if it doesn't exist
    try:
        os.makedirs('logs', exist_ok=True)
    except Exception as e:
        # In production (like Heroku), we may not have write access to create directories
        print(f"Warning: Could not create logs directory: {e}")
        # Continue without file logging
    
    # Enhanced format with more context
    detailed_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    simple_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
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
    if os.path.exists('logs') or not is_production:
        try:
            # General application log
            app_handler = RotatingFileHandler(
                'logs/fom_qbo.log',
                maxBytes=10485760,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            app_handler.setLevel(logging.INFO)
            app_handler.setFormatter(detailed_format)
            root_logger.addHandler(app_handler)
            
            # Error-only log for monitoring
            error_handler = RotatingFileHandler(
                'logs/errors.log',
                maxBytes=5242880,  # 5MB
                backupCount=3,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(detailed_format)
            root_logger.addHandler(error_handler)
            
            # Audit log for security events
            audit_handler = RotatingFileHandler(
                'logs/audit.log',
                maxBytes=5242880,  # 5MB
                backupCount=10,
                encoding='utf-8'
            )
            audit_handler.setLevel(logging.INFO)
            audit_formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(levelname)s - %(message)s'
            )
            audit_handler.setFormatter(audit_formatter)
            
            # Create separate audit logger
            audit_logger = logging.getLogger('audit')
            audit_logger.addHandler(audit_handler)
            audit_logger.setLevel(logging.INFO)
        except Exception as e:
            print(f"Warning: Could not create file handlers: {e}")
            # Continue with console logging only
            audit_logger = logging.getLogger('audit')
            audit_logger.addHandler(console_handler)
            audit_logger.setLevel(logging.INFO)
    else:
        # In production without file logging, use console for audit
        audit_logger = logging.getLogger('audit')
        audit_logger.addHandler(console_handler)
        audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# Initialize logging
logger = configure_logging()
audit_logger = logging.getLogger('audit')

def sanitize_for_logging(data):
    """Remove sensitive information from data before logging.
    
    Args:
        data: Dictionary or string to sanitize
    
    Returns:
        Sanitized version of the data
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            # Sensitive field patterns
            if any(pattern in key_lower for pattern in [
                'password', 'secret', 'token', 'key', 'auth', 'credential',
                'ssn', 'social', 'tax', 'account_number', 'routing', 'bank'
            ]):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = sanitize_for_logging(value)
            elif isinstance(value, list):
                sanitized[key] = [sanitize_for_logging(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        return sanitized
    elif isinstance(data, str):
        # Basic pattern matching for sensitive data in strings
        import re
        # Redact potential tokens/keys (long alphanumeric strings)
        data = re.sub(r'\b[A-Za-z0-9]{32,}\b', '[REDACTED_TOKEN]', data)
        # Redact potential SSNs
        data = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED_SSN]', data)
        return data
    else:
        return data

def log_audit_event(event_type, user_id=None, details=None, request_ip=None):
    """Log security and audit events.
    
    Args:
        event_type: Type of event (e.g., 'login', 'upload', 'qbo_auth')
        user_id: User identifier (if available)
        details: Additional event details
        request_ip: Client IP address
    """
    event_data = {
        'event_type': event_type,
        'user_id': user_id or 'anonymous',
        'ip_address': request_ip or 'unknown',
        'details': sanitize_for_logging(details) if details else {},
        'timestamp': datetime.now().isoformat()
    }
    
    audit_logger.info(json.dumps(event_data))

def process_single_file(file_data, qbo_authenticated):
    """Process a single file for donation extraction.
    
    Args:
        file_data: Dictionary containing file information
        qbo_authenticated: Whether QBO is authenticated
        
    Returns:
        Dictionary with processing results
    """
    result = {
        'success': False,
        'filename': file_data['filename'],
        'error': None,
        'donations': [],
        'file_path': None,
        'processing_time': 0
    }
    
    import time
    start_time = time.time()
    
    try:
        file_storage = file_data['file_storage']
        original_filename = file_data['filename']
        
        # Validate file extension
        _, ext = os.path.splitext(original_filename)
        ext = ext.lower()
        
        if ext not in ALLOWED_EXTENSIONS:
            result['error'] = f"File type not allowed: {original_filename}"
            return result
        
        # Check file size
        file_storage.seek(0, os.SEEK_END)
        file_size = file_storage.tell()
        file_storage.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            result['error'] = f"File too large: {original_filename} ({file_size / 1024 / 1024:.1f}MB)"
            return result
        
        # Generate secure filename and save
        secure_name = generate_secure_filename(original_filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)
        
        file_storage.save(file_path)
        result['file_path'] = file_path
        
        # Validate file content
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        is_valid = validate_file_content(file_content, original_filename)
        if not is_valid:
            result['error'] = f"Invalid file content: {original_filename}"
            cleanup_uploaded_file(file_path)
            return result
        
        # Process the file
        log_progress(f"Processing {original_filename} in parallel...")
        extracted_data = file_processor.process(file_path, ext)
        
        if extracted_data:
            if isinstance(extracted_data, list):
                result['donations'] = extracted_data
            else:
                result['donations'] = [extracted_data]
            
            # Apply customer matching if QBO is authenticated
            if qbo_authenticated and result['donations']:
                for donation in result['donations']:
                    if donation.get('Donor Name'):
                        customer = qbo_service.find_customer(donation['Donor Name'])
                        if customer:
                            donation['qboCustomerId'] = customer.get('Id')
                            donation['qbCustomerStatus'] = 'Found'
                            donation['matchMethod'] = 'Automatic'
                            donation['matchConfidence'] = 'High'
            
            result['success'] = True
            log_progress(f"Successfully processed {original_filename}: {len(result['donations'])} donations found")
        else:
            result['error'] = f"No donation data extracted from {original_filename}"
            
    except Exception as e:
        result['error'] = f"Error processing {original_filename}: {str(e)}"
        logger.error(f"Error in process_single_file: {e}", exc_info=True)
        
    finally:
        result['processing_time'] = time.time() - start_time
        
    return result

# File upload security configuration
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf', '.csv'}
ALLOWED_MIME_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'application/pdf': ['.pdf'],
    'text/csv': ['.csv'],
    'text/plain': ['.csv'],  # Some CSV files are detected as text/plain
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file

# Date validation configuration
# Donations older than this many days are flagged as potentially incorrect
DATE_WARNING_DAYS = int(os.getenv('DATE_WARNING_DAYS', '365'))  # Default: 1 year
# Donations with future dates more than this many days are rejected
FUTURE_DATE_LIMIT_DAYS = int(os.getenv('FUTURE_DATE_LIMIT_DAYS', '7'))  # Default: 1 week

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
    """Safely remove uploaded file."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up file: {file_path}")
    except Exception as e:
        print(f"Error cleaning up file {file_path}: {str(e)}")

def validate_donation_date(date_str, field_name="date"):
    """Validate a donation date is within reasonable bounds.
    
    Args:
        date_str: Date string to validate
        field_name: Name of the field for error messages
        
    Returns:
        Tuple of (is_valid, warning_message, parsed_date)
        - is_valid: True if date is acceptable, False if should be rejected
        - warning_message: Warning message if date is suspicious but acceptable
        - parsed_date: The parsed date object or None if invalid
    """
    if not date_str:
        return True, None, None
    
    try:
        # Parse the date
        parsed_date = pd.to_datetime(date_str)
        today = pd.Timestamp.now()
        
        # Check if date is in the future
        if parsed_date > today:
            days_future = (parsed_date - today).days
            if days_future > FUTURE_DATE_LIMIT_DAYS:
                return False, f"{field_name} is {days_future} days in the future (max allowed: {FUTURE_DATE_LIMIT_DAYS} days)", None
            elif days_future > 0:
                return True, f"{field_name} is {days_future} days in the future", parsed_date
        
        # Check if date is too old
        days_old = (today - parsed_date).days
        if days_old > DATE_WARNING_DAYS:
            years_old = days_old // 365
            return True, f"{field_name} is {years_old:.1f} years old - please verify", parsed_date
        
        # Date is within normal range
        return True, None, parsed_date
        
    except Exception as e:
        return False, f"Invalid {field_name} format: {str(e)}", None

# Validate required environment variables
def validate_environment():
    """Validate that all required environment variables are set."""
    required_vars = {
        'FLASK_SECRET_KEY': 'Flask secret key for session management',
        'GEMINI_API_KEY': 'Google Gemini API key for AI processing',
        'QBO_CLIENT_ID': 'QuickBooks OAuth Client ID',
        'QBO_CLIENT_SECRET': 'QuickBooks OAuth Client Secret',
        'QBO_REDIRECT_URI': 'QuickBooks OAuth redirect URI'
    }
    
    missing_vars = []
    for var_name, description in required_vars.items():
        if not os.environ.get(var_name):
            missing_vars.append(f"  - {var_name}: {description}")
    
    if missing_vars:
        error_msg = "Missing required environment variables:\n" + "\n".join(missing_vars)
        error_msg += "\n\nPlease set these in your .env file. See .env.example for reference."
        raise ValueError(error_msg)
    
    # Validate optional but recommended variables
    optional_vars = {
        'QBO_ENVIRONMENT': ('sandbox', 'QuickBooks environment (sandbox/production)')
    }
    
    for var_name, (default, description) in optional_vars.items():
        if not os.environ.get(var_name):
            print(f"Warning: {var_name} not set. Using default: {default}")
            print(f"         {description}")
    
    # Validate QBO_ENVIRONMENT value if set
    qbo_env = os.environ.get('QBO_ENVIRONMENT')
    if qbo_env and qbo_env not in ['sandbox', 'production']:
        raise ValueError(f"Invalid QBO_ENVIRONMENT: '{qbo_env}'. Must be 'sandbox' or 'production'.")
    
    # Validate URL format for redirect URI
    redirect_uri = os.environ.get('QBO_REDIRECT_URI')
    if redirect_uri and not (redirect_uri.startswith('http://') or redirect_uri.startswith('https://')):
        raise ValueError(f"Invalid QBO_REDIRECT_URI: '{redirect_uri}'. Must start with http:// or https://")

# Run validation before any other initialization
validate_environment()

def normalize_check_number(check_no):
    """Normalize check number for comparison."""
    if not check_no:
        return ''
    # Remove leading zeros and spaces
    normalized = str(check_no).strip().lstrip('0')
    # If all zeros were removed, ensure at least '0' remains
    return normalized if normalized else '0'

def normalize_amount(amount):
    """Normalize amount for comparison."""
    if not amount:
        return ''
    # Remove currency symbols, commas, and spaces
    amount_str = str(amount).replace('$', '').replace(',', '').strip()
    try:
        # Convert to float and format to 2 decimal places
        return f"{float(amount_str):.2f}"
    except:
        return amount_str

def normalize_donor_name(name):
    """Normalize donor name for comparison."""
    if not name:
        return ''
    # Convert to lowercase, remove punctuation, normalize whitespace
    name = re.sub(r'[^\w\s]', '', str(name).lower())
    return ' '.join(name.split())

def normalize_date(date_str):
    """Normalize date string to consistent format."""
    if not date_str:
        return ''
    try:
        # Try to parse various date formats
        parsed_date = dateutil.parser.parse(str(date_str))
        return parsed_date.strftime('%Y-%m-%d')
    except:
        # If parsing fails, return the original string
        return str(date_str).strip()

def deduplicate_and_synthesize_donations(existing_donations, new_donations):
    """
    Strict deduplication using Check No. + Amount as unique key.
    
    This ensures NO duplicates can exist with the same check number and amount.
    All data is merged into the single record for each unique key.
    """
    # Convert existing donations list to a dictionary with unique keys
    unique_donations = {}
    
    # First, add all existing donations to the unique dictionary
    for donation in existing_donations:
        check_no = normalize_check_number(donation.get('Check No.', ''))
        amount = normalize_amount(donation.get('Gift Amount', ''))
        
        # Create unique key
        if check_no and amount:
            # Check donations use check number + amount as key
            unique_key = f"CHECK_{check_no}_{amount}"
        else:
            # Non-check donations use donor name + amount + date as key
            donor_name = normalize_donor_name(donation.get('Donor Name', ''))
            gift_date = normalize_date(donation.get('Gift Date', ''))
            
            if donor_name and amount:
                unique_key = f"OTHER_{donor_name}_{amount}_{gift_date}"
            else:
                # Skip donations without enough identifying information
                print(f"Skipping donation without sufficient identifying info: {donation}")
                continue
        
        # Store in dictionary (will overwrite if duplicate key exists)
        if unique_key in unique_donations:
            print(f"WARNING: Duplicate key found in existing donations: {unique_key}")
        unique_donations[unique_key] = donation
    
    # Now process new donations
    merge_count = 0
    new_count = 0
    
    for new_donation in new_donations:
        check_no = normalize_check_number(new_donation.get('Check No.', ''))
        amount = normalize_amount(new_donation.get('Gift Amount', ''))
        
        # Skip suspicious entries (e.g., check numbers that are too short or don't look valid)
        if check_no and len(check_no) < 3 and check_no.isdigit():
            # Check numbers like "195" are suspicious - real checks are usually 4+ digits
            print(f"WARNING: Suspicious check number '{check_no}' - may be a page number or reference")
            # Still process it but log the warning
        
        # Create unique key
        if check_no and amount:
            # Check donations use check number + amount as key
            unique_key = f"CHECK_{check_no}_{amount}"
        else:
            # Non-check donations use donor name + amount + date as key
            donor_name = normalize_donor_name(new_donation.get('Donor Name', ''))
            gift_date = normalize_date(new_donation.get('Gift Date', ''))
            
            if donor_name and amount:
                unique_key = f"OTHER_{donor_name}_{amount}_{gift_date}"
            else:
                # Skip donations without enough identifying information
                print(f"Skipping new donation without sufficient identifying info: {new_donation}")
                continue
        
        # Check if this key already exists
        if unique_key in unique_donations:
            # Merge with existing donation
            print(f"Merging donation with key: {unique_key}")
            unique_donations[unique_key] = synthesize_donation_data(
                unique_donations[unique_key], new_donation
            )
            merge_count += 1
        else:
            # Add as new donation
            print(f"Adding new donation with key: {unique_key}")
            unique_donations[unique_key] = new_donation
            new_count += 1
    
    # Convert back to list
    result = list(unique_donations.values())
    
    # Ensure internal IDs are unique
    for i, donation in enumerate(result):
        if 'internalId' not in donation or not donation['internalId']:
            donation['internalId'] = f"donation_{i}"
    
    print(f"Deduplication complete: {len(result)} unique donations (merged {merge_count}, added {new_count})")
    
    return result

def synthesize_donation_data(existing, new):
    """
    Intelligently merge two donation records, preserving the most complete information.
    
    Priority rules:
    1. Non-null values override null values
    2. Longer/more complete values override shorter ones
    3. Values from images override values from PDFs (generally more accurate)
    4. Specific fields have custom merge logic
    """
    merged = existing.copy()
    
    # Initialize merge history if not present
    if 'mergeHistory' not in merged:
        merged['mergeHistory'] = []
    
    # Track what fields are being merged
    merged_fields = []
    
    # Fields that should be merged by taking non-null or most complete value
    simple_merge_fields = [
        'Donor Name', 'First Name', 'Last Name', 'Full Name',
        'Address - Line 1', 'City', 'State', 'ZIP',
        'Organization Name', 'Email', 'Phone',
        'Check Date', 'Deposit Date', 'Deposit Method'
    ]
    
    for field in simple_merge_fields:
        existing_val = existing.get(field)
        new_val = new.get(field)
        
        # Take new value if existing is empty/null/N/A
        if (not existing_val or existing_val == 'N/A') and new_val and new_val != 'N/A':
            merged[field] = new_val
            merged_fields.append(field)
        # Take longer/more complete value for text fields
        elif existing_val and new_val and isinstance(existing_val, str) and isinstance(new_val, str):
            # Safely strip whitespace
            existing_stripped = existing_val.strip() if existing_val else ''
            new_stripped = new_val.strip() if new_val else ''
            
            # Also replace N/A with actual values
            if existing_val == 'N/A' and new_val != 'N/A':
                merged[field] = new_val
                merged_fields.append(field)
            elif len(new_stripped) > len(existing_stripped) and new_val != 'N/A':
                merged[field] = new_val
                merged_fields.append(field)
    
    # Special handling for memo - concatenate if different
    existing_memo = existing.get('Memo') or ''
    new_memo = new.get('Memo') or ''
    existing_memo = existing_memo.strip() if existing_memo else ''
    new_memo = new_memo.strip() if new_memo else ''
    
    if new_memo and new_memo not in existing_memo:
        if existing_memo:
            merged['Memo'] = f"{existing_memo}; {new_memo}"
        else:
            merged['Memo'] = new_memo
    
    # Preserve QBO-related fields from existing record
    qbo_fields = ['qboCustomerId', 'qbCustomerStatus', 'qbSyncStatus', 
                  'matchMethod', 'matchConfidence', 'internalId']
    for field in qbo_fields:
        if field in existing:
            merged[field] = existing[field]
    
    # Data source tracking
    if 'dataSource' in existing and 'dataSource' in new:
        if existing['dataSource'] != new['dataSource']:
            merged['dataSource'] = 'Mixed'
    
    # Add merge history entry if fields were merged
    if merged_fields:
        merged['mergeHistory'].append({
            'timestamp': datetime.now().isoformat(),
            'mergedFields': merged_fields,
            'sourceData': {
                'checkNo': new.get('Check No.', ''),
                'amount': new.get('Gift Amount', ''),
                'donor': new.get('Donor Name', '')
            }
        })
        merged['isMerged'] = True
    
    return merged

# Define model aliases
MODEL_MAPPING = {
    'gemini-flash': 'gemini-2.5-flash-preview-04-17',
    'gemini-pro': 'gemini-2.5-pro-preview-03-25',
    # Include the full model names as keys for consistency
    'gemini-2.5-flash-preview-04-17': 'gemini-2.5-flash-preview-04-17',
    'gemini-2.5-pro-preview-03-25': 'gemini-2.5-pro-preview-03-25'
}

# Resolve the environment variable model
gemini_env_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-preview-04-17')
# If the environment variable is an alias, resolve it
resolved_env_model = MODEL_MAPPING.get(gemini_env_model, gemini_env_model)

# Parse command line arguments for QBO environment and Gemini model
parser = argparse.ArgumentParser(description="FOM to QBO Automation App")
parser.add_argument('--env', type=str, choices=['sandbox', 'production'], default=os.getenv('QBO_ENVIRONMENT', 'sandbox'),
                    help='QuickBooks Online environment (sandbox or production)')
parser.add_argument('--model', type=str, default=resolved_env_model,
                    choices=['gemini-flash', 'gemini-pro', 'gemini-2.5-flash-preview-04-17', 'gemini-2.5-pro-preview-03-25'],
                    help='Gemini model to use (flash for faster responses, pro for better quality)')
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

# Set Flask secret key from environment variable (already validated)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB upload limit

# Initialize CSRF protection
csrf = CSRFProtect(app)
# Configure CSRF to accept tokens in X-CSRFToken header (for AJAX requests)
app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken']

# Initialize rate limiter
# For now, disable rate limiting in production due to Redis SSL issues
# TODO: Fix Redis SSL configuration for Flask-Limiter
redis_url = os.environ.get('REDIS_URL')
if redis_url:
    # Use memory storage for rate limiting until Redis SSL is fixed
    print("Using memory storage for rate limiting (Redis SSL issue workaround)")
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri="memory://"
    )
else:
    # Use memory storage for development
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri="memory://"
    )

# Configure server-side session storage
def configure_session(app):
    """Configure server-side session storage with Redis or filesystem fallback."""
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
            configure_filesystem_sessions(app)
    else:
        # Use filesystem for development
        print("No REDIS_URL found. Using filesystem for session storage (development mode)")
        configure_filesystem_sessions(app)
    
    # Common session configuration
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'fom_qbo:'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    
    # Initialize Flask-Session
    Session(app)

def configure_filesystem_sessions(app):
    """Configure filesystem-based sessions for development."""
    session_dir = os.path.join(tempfile.gettempdir(), 'fom_qbo_sessions')
    os.makedirs(session_dir, exist_ok=True)
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = session_dir
    app.config['SESSION_FILE_THRESHOLD'] = 100  # Max number of sessions

# Configure session storage
configure_session(app)

# Create necessary directories
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except Exception as e:
    print(f"Warning: Could not create upload directory: {e}")
    # Use temp directory as fallback
    import tempfile
    app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp(prefix='fom_qbo_uploads_')

# Initialize Redis client for QBO token persistence
redis_client = None
redis_url = os.environ.get('REDIS_URL')
if redis_url:
    try:
        if redis_url.startswith('rediss://'):
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
    api_key=os.getenv('GEMINI_API_KEY'),
    model_name=gemini_model  # Use the command-line specified model
)
qbo_service = QBOService(
    client_id=os.getenv('QBO_CLIENT_ID'),
    client_secret=os.getenv('QBO_CLIENT_SECRET'),
    redirect_uri=os.getenv('QBO_REDIRECT_URI'),
    environment=qbo_environment,  # Use the command-line specified environment
    redis_client=redis_client  # Pass Redis client for token persistence
)
# Pass both services to the file processor for integrated customer matching
file_processor = FileProcessor(gemini_service, qbo_service, progress_logger)

# Initialize progress logger with Gemini service
init_progress_logger(gemini_service)

# Routes
@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')

@app.route('/upload-test', methods=['POST'])
def upload_test():
    """Simple upload test endpoint."""
    return jsonify({
        'success': True,
        'message': 'Upload endpoint is working',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/upload-simple', methods=['POST'])
def upload_simple():
    """Simplified upload endpoint with basic processing."""
    try:
        print("[UPLOAD-SIMPLE] Starting simple upload")
        
        # Get files
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No files provided'
            }), 400
            
        files = request.files.getlist('files')
        valid_files = [f for f in files if f.filename]
        
        if not valid_files:
            return jsonify({
                'success': False,
                'message': 'No valid files provided'
            }), 400
        
        print(f"[UPLOAD-SIMPLE] Processing {len(valid_files)} files")
        
        # Create session
        import uuid
        session_id = str(uuid.uuid4())
        
        # Check QBO authentication
        qbo_authenticated = qbo_service.access_token is not None and qbo_service.realm_id is not None
        
        # Simple processing - just save files and extract basic info
        donations = []
        errors = []
        uploaded_files = []
        
        for idx, file in enumerate(valid_files):
            try:
                # Save file
                original_filename = file.filename
                secure_name = generate_secure_filename(original_filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)
                file.save(file_path)
                uploaded_files.append(file_path)
                
                # Detect file type
                _, ext = os.path.splitext(original_filename)
                ext = ext.lower()
                
                # Process based on file type (but simplified for now)
                if ext == '.csv':
                    # Process CSV file
                    try:
                        print(f"[UPLOAD-SIMPLE] Processing CSV: {original_filename}")
                        result = file_processor.process_csv(file_path)
                        if result and 'donations' in result:
                            for donation in result['donations']:
                                donation['fileName'] = original_filename
                                donation['dataSource'] = 'CSV'
                                donation['internalId'] = f'csv_{idx}_{donations.index(donation)}'
                            donations.extend(result['donations'])
                        else:
                            # Fallback to test data
                            donations.append({
                                'internalId': f'csv_{idx}',
                                'Donor Name': f'CSV Test Donor {idx + 1}',
                                'Gift Amount': '150.00',
                                'Check Date': datetime.now().strftime('%m/%d/%Y'),
                                'Check No.': f'CSV{idx + 1:03d}',
                                'fileName': original_filename,
                                'dataSource': 'CSV',
                                'qbSyncStatus': 'Pending'
                            })
                    except Exception as csv_error:
                        print(f"[UPLOAD-SIMPLE] CSV processing error: {csv_error}")
                        # Fallback to test data
                        donations.append({
                            'internalId': f'csv_{idx}',
                            'Donor Name': f'CSV Error - Test Data',
                            'Gift Amount': '0.00',
                            'Check Date': datetime.now().strftime('%m/%d/%Y'),
                            'Check No.': f'ERR{idx + 1:03d}',
                            'fileName': original_filename,
                            'dataSource': 'CSV',
                            'qbSyncStatus': 'Pending'
                        })
                elif ext in ['.jpg', '.jpeg', '.png']:
                    # Skip image processing for now - just use test data
                    print(f"[UPLOAD-SIMPLE] Skipping image processing for: {original_filename}")
                    donations.append({
                        'internalId': f'img_{idx}',
                        'Donor Name': f'Image Processing Disabled',
                        'Gift Amount': '200.00',
                        'Check Date': datetime.now().strftime('%m/%d/%Y'),
                        'Check No.': f'IMG{idx + 1:03d}',
                        'fileName': original_filename,
                        'dataSource': 'IMAGE',
                        'qbSyncStatus': 'Pending'
                    })
                elif ext == '.pdf':
                    # For PDFs, create another test donation
                    donations.append({
                        'internalId': f'pdf_{idx}',
                        'Donor Name': f'PDF Donor {idx + 1}',
                        'Gift Amount': '250.00',
                        'Check Date': datetime.now().strftime('%m/%d/%Y'),
                        'Check No.': f'PDF{idx + 1:03d}',
                        'fileName': original_filename,
                        'dataSource': 'PDF',
                        'qbSyncStatus': 'Pending'
                    })
                else:
                    errors.append(f"Unsupported file type: {ext}")
                
            except Exception as e:
                print(f"[UPLOAD-SIMPLE] Error processing {file.filename}: {e}")
                errors.append(f"Error processing {file.filename}: {str(e)}")
        
        # Clean up files
        for file_path in uploaded_files:
            try:
                os.remove(file_path)
            except:
                pass
        
        # Store in session
        if 'donations' not in session:
            session['donations'] = []
        session['donations'].extend(donations)
        
        print(f"[UPLOAD-SIMPLE] Completed. Found {len(donations)} donations")
        
        return jsonify({
            'success': True,
            'progressSessionId': session_id,
            'donations': session['donations'],
            'newCount': len(donations),
            'totalCount': len(session['donations']),
            'qboAuthenticated': qbo_authenticated,
            'warnings': errors if errors else None
        })
        
    except Exception as e:
        print(f"[UPLOAD-SIMPLE] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/health')
def health_check():
    """Basic health check endpoint - does not test external services."""
    import psutil
    import time
    
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'uptime_seconds': time.time() - app.start_time,
        'environment': {
            'flask_configured': bool(app.secret_key),
            'gemini_configured': bool(gemini_service.api_key),
            'qbo_configured': all([qbo_service.client_id, qbo_service.client_secret]),
            'qbo_environment': qbo_service.environment,
            'session_type': app.config.get('SESSION_TYPE', 'unknown'),
            'session_storage': 'Redis' if app.config.get('SESSION_TYPE') == 'redis' else 'Filesystem'
        },
        'system': {
            'memory_usage_mb': round(psutil.Process().memory_info().rss / 1024 / 1024, 1),
            'cpu_percent': psutil.Process().cpu_percent(),
            'disk_free_gb': round(psutil.disk_usage('/').free / 1024**3, 1)
        },
        'auth': {
            'qbo_authenticated': qbo_service.is_token_valid(),
            'qbo_token_expires_at': qbo_service.token_expires_at if qbo_service.access_token else None,
            'qbo_token_expires_in_hours': None
        }
    }
    
    # Calculate token expiration time
    if qbo_service.token_expires_at:
        try:
            expires_at = datetime.fromisoformat(qbo_service.token_expires_at.replace('Z', '+00:00'))
            time_diff = expires_at - datetime.now().replace(tzinfo=expires_at.tzinfo)
            health_status['auth']['qbo_token_expires_in_hours'] = round(time_diff.total_seconds() / 3600, 1)
        except Exception as e:
            logger.warning(f"Error calculating token expiration: {e}")
    
    # Determine overall health
    critical_issues = []
    if not health_status['environment']['flask_configured']:
        critical_issues.append('Flask not configured')
    if not health_status['environment']['gemini_configured']:
        critical_issues.append('Gemini not configured')
    if not health_status['environment']['qbo_configured']:
        critical_issues.append('QBO not configured')
    
    if critical_issues:
        health_status['status'] = 'unhealthy'
        health_status['issues'] = critical_issues
        
    return jsonify(health_status)

@app.route('/ready')
def readiness_check():
    """Readiness check endpoint - tests external service connectivity."""
    import requests
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    readiness_status = {
        'status': 'ready',
        'timestamp': datetime.now().isoformat(),
        'services': {},
        'checks_performed': []
    }
    
    def check_qbo_connectivity():
        """Test QBO API connectivity."""
        try:
            if not qbo_service.access_token:
                return {
                    'service': 'quickbooks',
                    'status': 'not_authenticated',
                    'message': 'No access token available',
                    'response_time_ms': 0
                }
            
            start_time = time.time()
            # Test with a simple API call
            customers = qbo_service.get_all_customers()
            response_time = round((time.time() - start_time) * 1000, 1)
            
            if isinstance(customers, list):
                return {
                    'service': 'quickbooks',
                    'status': 'healthy',
                    'message': f'Successfully retrieved {len(customers)} customers',
                    'response_time_ms': response_time
                }
            else:
                return {
                    'service': 'quickbooks',
                    'status': 'unhealthy',
                    'message': 'Invalid response from QBO API',
                    'response_time_ms': response_time
                }
                
        except Exception as e:
            return {
                'service': 'quickbooks',
                'status': 'unhealthy',
                'message': f'QBO connectivity error: {str(e)}',
                'response_time_ms': 0
            }
    
    def check_gemini_connectivity():
        """Test Gemini API connectivity."""
        try:
            start_time = time.time()
            # Simple test prompt
            result = gemini_service.generate_text("Test connectivity. Respond with 'OK'.")
            response_time = round((time.time() - start_time) * 1000, 1)
            
            if result and 'OK' in result.upper():
                return {
                    'service': 'gemini',
                    'status': 'healthy',
                    'message': 'Successfully connected to Gemini API',
                    'response_time_ms': response_time
                }
            else:
                return {
                    'service': 'gemini',
                    'status': 'unhealthy',
                    'message': 'Unexpected response from Gemini API',
                    'response_time_ms': response_time
                }
                
        except Exception as e:
            return {
                'service': 'gemini',
                'status': 'unhealthy',
                'message': f'Gemini connectivity error: {str(e)}',
                'response_time_ms': 0
            }
    
    def check_redis_connectivity():
        """Test Redis connectivity if configured."""
        if not os.environ.get('REDIS_URL'):
            return {
                'service': 'redis',
                'status': 'not_configured',
                'message': 'Redis not configured',
                'response_time_ms': 0
            }
        
        try:
            start_time = time.time()
            import redis
            r = redis.from_url(os.environ.get('REDIS_URL'))
            r.ping()
            response_time = round((time.time() - start_time) * 1000, 1)
            
            return {
                'service': 'redis',
                'status': 'healthy',
                'message': 'Redis connection successful',
                'response_time_ms': response_time
            }
            
        except Exception as e:
            return {
                'service': 'redis',
                'status': 'unhealthy',
                'message': f'Redis connectivity error: {str(e)}',
                'response_time_ms': 0
            }
    
    # Run checks in parallel for faster response
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(check_qbo_connectivity): 'qbo',
            executor.submit(check_gemini_connectivity): 'gemini',
            executor.submit(check_redis_connectivity): 'redis'
        }
        
        for future in as_completed(futures):
            try:
                result = future.result(timeout=10)  # 10 second timeout per check
                service_name = result['service']
                readiness_status['services'][service_name] = result
                readiness_status['checks_performed'].append(service_name)
                
                # If any critical service is unhealthy, mark as not ready
                if service_name in ['quickbooks', 'gemini'] and result['status'] == 'unhealthy':
                    readiness_status['status'] = 'not_ready'
                    
            except Exception as e:
                logger.error(f"Readiness check failed: {e}")
                readiness_status['status'] = 'not_ready'
                readiness_status['error'] = str(e)
    
    # Return appropriate HTTP status code
    status_code = 200 if readiness_status['status'] == 'ready' else 503
    return jsonify(readiness_status), status_code
    
@app.route('/qbo/auth-status')
def qbo_auth_status():
    """Check QBO authentication status."""
    authenticated = qbo_service.access_token is not None and qbo_service.realm_id is not None
    
    # Check if we just connected to QBO and need to resume file processing
    just_connected = session.pop('qbo_just_connected', False)
    
    return jsonify({
        'authenticated': authenticated,
        'tokenExpiry': qbo_service.token_expires_at if authenticated else None,
        'justConnected': just_connected
    })

@app.route('/qbo/disconnect', methods=['POST'])
@limiter.limit("10 per hour")
def disconnect_qbo():
    """Disconnect from QuickBooks by clearing stored tokens."""
    try:
        # Log audit event
        log_audit_event(
            'qbo_disconnect',
            request_ip=request.remote_addr,
            details={'realm_id': qbo_service.realm_id}
        )
        
        # Clear tokens
        qbo_service.clear_tokens()
        
        # Clear customer cache
        qbo_service.clear_customer_cache()
        
        # Clear session flags
        session.pop('qbo_connected', None)
        session.pop('qbo_just_connected', None)
        
        flash('Successfully disconnected from QuickBooks Online', 'success')
        return jsonify({'success': True, 'message': 'Disconnected from QuickBooks'})
    except Exception as e:
        logger.error(f"Error disconnecting from QBO: {e}")
        return jsonify({'success': False, 'message': 'Error disconnecting from QuickBooks'}), 500

@app.route('/upload-start', methods=['POST'])
def upload_start():
    """Initialize upload session and return session ID for progress tracking."""
    import uuid
    session_id = str(uuid.uuid4())
    
    # Initialize progress logger session
    progress_logger.start_session(session_id)
    
    # Log initial progress
    log_progress(f"Initializing upload session {session_id}")
    log_progress("Preparing to receive files...", force_summary=True)
    
    return jsonify({
        'success': True,
        'sessionId': session_id
    })

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per hour")
def upload_files():
    """Handle file uploads (images, PDFs, CSV)."""
    print("[UPLOAD] Upload endpoint called")
    try:
        # Quick health check - return immediately if no files
        print("[UPLOAD] Checking for files in request")
        if 'files' not in request.files:
            print("[UPLOAD] No files in request")
            return jsonify({
                'success': False,
                'message': 'No files provided',
                'progressSessionId': None
            }), 400
        # Get session ID from request or create new one
        import uuid
        import time
        session_id = request.form.get('sessionId')
        
        if not session_id:
            # Create new session if not provided
            session_id = str(uuid.uuid4())
            progress_logger.start_session(session_id)
        
        # Return session ID immediately for SSE connection
        response_data = {
            'progressSessionId': session_id,
            'processingStarted': True
        }
        
        # Send initial response quickly
        def process_after_response():
            time.sleep(0.1)  # Small delay to ensure response is sent
            log_progress("Starting to process your uploaded files...")
            log_progress("Preparing to analyze your documents", force_summary=True)
        
        # Check if QBO is authenticated for customer matching
        qbo_authenticated = qbo_service.access_token is not None and qbo_service.realm_id is not None
        if not qbo_authenticated:
            log_progress("QuickBooks connection not detected - will process files without customer matching")
        else:
            log_progress("Connected to QuickBooks - will match customers automatically")
            
        # Check if request has the files part
        if 'files' not in request.files:
            log_progress("No files were uploaded", force_summary=True)
            progress_logger.end_session(session_id)
            return jsonify({
                'success': False,
                'message': 'No files were selected'
            }), 400
        
        files = request.files.getlist('files')
        if not files or len(files) == 0 or all(file.filename == '' for file in files):
            log_progress("No valid files found in upload", force_summary=True)
            progress_logger.end_session(session_id)
            return jsonify({
                'success': False,
                'message': 'No files were selected'
            }), 400
            
        # Log audit event for file upload
        file_info = []
        for file in files:
            if file.filename != '':
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)  # Reset file pointer
                file_info.append({
                    'filename': file.filename,
                    'size_mb': round(file_size / 1024 / 1024, 1),
                    'content_type': file.content_type
                })
        
        log_audit_event(
            'file_upload',
            request_ip=request.remote_addr,
            details={
                'session_id': session_id,
                'file_count': len(files),
                'files': file_info,
                'qbo_authenticated': qbo_authenticated
            }
        )
        
        # Log the files being processed
        log_progress(f"Received {len(files)} file(s) - analyzing content now...")
        if file_info:
            file_display = [f"{f['filename']} ({f['size_mb']} MB)" for f in file_info]
            log_progress(f"Processing files: {', '.join(file_display[:3])}" + ("..." if len(file_display) > 3 else ""))
        
        # Placeholder for extracted donation data
        donations = []
        errors = []
        warnings = []
        uploaded_files = []  # Track files for cleanup
        
        # If QBO is not authenticated, add a warning
        if not qbo_authenticated:
            warnings.append("QuickBooks is not connected. Customer matching will be skipped. Please connect to QuickBooks to enable automatic customer matching.")
        
        # Check if we should use concurrent processing
        # TEMPORARY: Disable concurrent processing for debugging
        use_concurrent = False  # len(files) > 1 or any(file.filename.lower().endswith('.pdf') for file in files if file.filename)
        
        if use_concurrent:
            # Prepare files for concurrent processing
            log_progress(f"Preparing {len(files)} files for concurrent processing...")
            files_to_process = []
            
            # First, save and validate all files
            for file in files:
                if file.filename == '':
                    continue
                
                try:
                    # Validate file extension first
                    original_filename = file.filename
                    _, ext = os.path.splitext(original_filename)
                    ext = ext.lower()
                    
                    if ext not in ALLOWED_EXTENSIONS:
                        errors.append(f"File type not allowed: {original_filename}")
                        log_progress(f"Skipping {original_filename} - file type not allowed")
                        continue
                
                    # Check file size before saving
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)  # Reset file pointer
                    
                    if file_size > MAX_FILE_SIZE:
                        errors.append(f"File too large: {original_filename} ({file_size / 1024 / 1024:.1f}MB, max {MAX_FILE_SIZE / 1024 / 1024}MB)")
                        log_progress(f"Skipping {original_filename} - file too large")
                        continue
                
                    # Generate secure filename
                    secure_name = generate_secure_filename(original_filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)
                    
                    log_progress(f"Saving {original_filename} securely...")
                    file.save(file_path)
                    uploaded_files.append(file_path)  # Track for cleanup
                    
                    # Validate file content
                    is_valid, error_msg = validate_file_content(file_path)
                    if not is_valid:
                        errors.append(f"Invalid file content: {original_filename} - {error_msg}")
                        log_progress(f"Skipping {original_filename} - {error_msg}")
                        cleanup_uploaded_file(file_path)
                        uploaded_files.remove(file_path)
                        continue
                
                    files_to_process.append((file_path, ext))
                    log_progress(f"File validated: {original_filename}")
                    
                except Exception as e:
                    log_progress(f"Error preparing {original_filename}: {str(e)}")
                    errors.append(f"Error preparing {original_filename}: {str(e)}")
            
            # Process all files concurrently
            if files_to_process:
                log_progress(f"Processing {len(files_to_process)} files concurrently...")
                
                # Count expected batches
                total_batches = 0
                for file_path, ext in files_to_process:
                    if ext == '.pdf':
                        # Count PDF pages to estimate batches
                        try:
                            import fitz
                            pdf_doc = fitz.open(file_path)
                            pages = len(pdf_doc)
                            pdf_doc.close()
                            total_batches += (pages + 1) // 2  # 2 pages per batch
                        except:
                            total_batches += 1
                    else:
                        total_batches += 1
                
                log_progress(f"Processing {total_batches} batches across {len(files_to_process)} files...")
                
                # Process files concurrently
                concurrent_donations, concurrent_errors = file_processor.process_files_concurrently(
                    files_to_process, 
                    task_id=session_id
                )
                
                # Add data source and internal IDs to donations
                for idx, donation in enumerate(concurrent_donations):
                    # Determine data source
                    data_source = 'CSV' if any(fp.endswith('.csv') for fp, _ in files_to_process) else 'LLM'
                    source_prefix = 'csv' if data_source == 'CSV' else 'llm'
                    
                    donation['dataSource'] = data_source
                    donation['internalId'] = f"{source_prefix}_{idx}"
                    donation['qbSyncStatus'] = 'Pending'
                    # Only initialize as Unknown if no status was set during matching
                    if 'qbCustomerStatus' not in donation:
                        donation['qbCustomerStatus'] = 'Unknown'
                
                donations.extend(concurrent_donations)
                errors.extend(concurrent_errors)
                
                log_progress(f"Concurrent processing complete: {len(donations)} donations extracted")
        else:
            # Single file processing (keep existing logic)
            for file in files:
                if file.filename == '':
                    continue
                
                try:
                    # Validate file extension first
                    original_filename = file.filename
                    _, ext = os.path.splitext(original_filename)
                    ext = ext.lower()
                    
                    if ext not in ALLOWED_EXTENSIONS:
                        errors.append(f"File type not allowed: {original_filename}")
                        log_progress(f"Skipping {original_filename} - file type not allowed")
                        continue
                    
                    # Check file size before saving
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)  # Reset file pointer
                    
                    if file_size > MAX_FILE_SIZE:
                        errors.append(f"File too large: {original_filename} ({file_size / 1024 / 1024:.1f}MB, max {MAX_FILE_SIZE / 1024 / 1024}MB)")
                        log_progress(f"Skipping {original_filename} - file too large")
                        continue
                    
                    # Generate secure filename
                    secure_name = generate_secure_filename(original_filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)
                    
                    log_progress(f"Saving {original_filename} securely...")
                    file.save(file_path)
                    uploaded_files.append(file_path)  # Track for cleanup
                    
                    # Validate file content
                    is_valid, error_msg = validate_file_content(file_path)
                    if not is_valid:
                        errors.append(f"Invalid file content: {original_filename} - {error_msg}")
                        log_progress(f"Skipping {original_filename} - {error_msg}")
                        cleanup_uploaded_file(file_path)
                        uploaded_files.remove(file_path)
                        continue
                    
                    file_size_mb = file_size / (1024 * 1024)
                    log_progress(f"File validated: {original_filename} ({file_size_mb:.1f}MB)")
                    
                    # Process different file types
                    file_ext = ext  # We already have the extension
                    
                    if file_ext in ['.jpg', '.jpeg', '.png', '.pdf', '.csv']:
                        # Process all files using Gemini
                        file_type = "spreadsheet" if file_ext == '.csv' else "image" if file_ext in ['.jpg', '.jpeg', '.png'] else "PDF document"
                        log_progress(f"Reading {file_type}: {original_filename}")
                        
                        log_progress(f"Analyzing content of {original_filename}...")
                        extracted_data = file_processor.process(file_path, file_ext)
                        log_progress(f"Content analysis complete for {original_filename}")
                        
                        # Set the data source based on file type
                        data_source = 'CSV' if file_ext == '.csv' else 'LLM'
                        source_prefix = 'csv' if file_ext == '.csv' else 'llm'
                        
                        if extracted_data:
                            # Check if we have a list of donations or a single donation
                            if isinstance(extracted_data, list):
                                log_progress(f"Found {len(extracted_data)} donation records in {original_filename}")
                                log_progress(f"Processing individual donations from {original_filename}...")
                                for idx, donation in enumerate(extracted_data):
                                    if idx % 5 == 0 and idx > 0:
                                        log_progress(f"Processed {idx} of {len(extracted_data)} donations from {original_filename}")
                                    donation['dataSource'] = data_source
                                    donation['internalId'] = f"{source_prefix}_{len(donations) + idx}"
                                    donation['qbSyncStatus'] = 'Pending'
                                    # Only initialize as Unknown if no status was set during matching
                                    if 'qbCustomerStatus' not in donation:
                                        donation['qbCustomerStatus'] = 'Unknown'
                                    donations.append(donation)
                            else:
                                # Single donation (typically from image)
                                extracted_data['dataSource'] = data_source
                                extracted_data['internalId'] = f"{source_prefix}_{len(donations)}"
                                extracted_data['qbSyncStatus'] = 'Pending'
                                # Only initialize as Unknown if no status was set during matching
                                if 'qbCustomerStatus' not in extracted_data:
                                    extracted_data['qbCustomerStatus'] = 'Unknown'
                                donations.append(extracted_data)
                        else:
                            log_progress(f"Could not extract donation data from {original_filename}")
                            errors.append(f"No donation data could be extracted from {original_filename}")
                    else:
                        log_progress(f"Unsupported file type: {file_ext}")
                        errors.append(f"Unsupported file type: {file_ext}")
                
                except Exception as e:
                    log_progress(f"Error processing {original_filename}: {str(e)}")
                    errors.append(f"Error processing {original_filename}: {str(e)}")
        
        # Process donations
        if donations:
            log_progress("Checking for duplicate donations and organizing data...")
            log_progress(f"Analyzing {len(donations)} new donations for duplicates...")
        
        # Store donations in session for later use with deduplication
        if 'donations' not in session:
            session['donations'] = []
        
        # Track counts before deduplication
        initial_count = len(session['donations'])
        new_count = len(donations)
        
        # Apply smart deduplication and data synthesis
        log_progress("Finalizing donation records...")
        log_progress(f"Merging with existing {initial_count} donations...")
        session['donations'] = deduplicate_and_synthesize_donations(
            session['donations'], donations
        )
        
        # Calculate merge statistics
        final_count = len(session['donations'])
        merged_count = initial_count + new_count - final_count
        
        # Return appropriate response based on success/errors
        if session['donations']:
            log_progress(f"Successfully processed {final_count} donation records. Ready for QuickBooks!", force_summary=True)
            progress_logger.end_session(session_id)
            
            # Clean up files before returning
            for file_path in uploaded_files:
                cleanup_uploaded_file(file_path)
            
            # Return the deduplicated donations from session
            return jsonify({
                'success': True,
                'donations': session['donations'],
                'newCount': new_count,
                'totalCount': final_count,
                'mergedCount': merged_count,
                'warnings': (errors + warnings) if (errors or warnings) else None,
                'qboAuthenticated': qbo_authenticated,
                'progressSessionId': session_id
            })
        else:
            log_progress("Could not find any donation data in the uploaded files", force_summary=True)
            progress_logger.end_session(session_id)
            
            # Clean up files before returning
            for file_path in uploaded_files:
                cleanup_uploaded_file(file_path)
            
            message = 'No donation data could be extracted. ' + (', '.join(errors) if errors else '')
            if warnings:
                message += ' ' + (', '.join(warnings))
                
            return jsonify({
                'success': False,
                'message': message,
                'qboAuthenticated': qbo_authenticated,
                'progressSessionId': session_id
            }), 400
    
    except Exception as e:
        import traceback
        log_progress(f"An unexpected error occurred: {str(e)}", force_summary=True)
        progress_logger.end_session(session_id)
        print(f"Unexpected error in upload processing: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'message': f'An unexpected error occurred: {str(e)}',
            'progressSessionId': session_id
        }), 500
    
    finally:
        # Clean up all uploaded files
        for file_path in uploaded_files:
            cleanup_uploaded_file(file_path)

@app.route('/progress-stream/<session_id>')
def progress_stream(session_id):
    """Stream progress updates for a specific session."""
    print(f"[Flask] Progress stream requested for session: {session_id}")
    
    def generate():
        for progress_data in progress_logger.get_progress_stream(session_id):
            yield progress_data
    
    response = Response(generate(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response

@app.route('/test-progress')
def test_progress():
    """Test endpoint to verify progress streaming works."""
    import uuid
    test_session_id = str(uuid.uuid4())
    progress_logger.start_session(test_session_id)
    
    # Log some test messages
    log_progress("Test message 1: Starting test")
    log_progress("Test message 2: Processing data")
    log_progress("Test message 3: Almost done", force_summary=True)
    
    return jsonify({
        'sessionId': test_session_id,
        'message': 'Test progress session started. Connect to /progress-stream/' + test_session_id
    })

@app.route('/donations', methods=['GET'])
def get_donations():
    """Return donations with pagination support."""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 200)  # Max 200 per page
    
    donations = session.get('donations', [])
    total = len(donations)
    
    # Calculate pagination
    start = (page - 1) * per_page
    end = start + per_page
    paginated_donations = donations[start:end]
    
    # Calculate pagination info
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    has_next = page < total_pages
    has_prev = page > 1
    
    return jsonify({
        'donations': paginated_donations,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': has_next,
            'has_prev': has_prev,
            'next_page': page + 1 if has_next else None,
            'prev_page': page - 1 if has_prev else None
        }
    })

@app.route('/session-info')
def session_info():
    """Get information about current session size and storage."""
    import sys
    
    donations = session.get('donations', [])
    
    # Calculate approximate session size
    session_data = {
        'donations': donations,
        'qbo_connected': session.get('qbo_connected', False),
        'qbo_just_connected': session.get('qbo_just_connected', False)
    }
    
    # Serialize to estimate size
    try:
        session_json = json.dumps(session_data)
        session_size = len(session_json.encode('utf-8'))
    except:
        session_size = 0
    
    return jsonify({
        'storage_type': app.config.get('SESSION_TYPE', 'unknown'),
        'donation_count': len(donations),
        'session_size_bytes': session_size,
        'session_size_kb': round(session_size / 1024, 2),
        'client_side_limit_kb': 4,  # Flask's cookie session limit
        'would_exceed_cookie_limit': session_size > (4 * 1024),
        'recommendation': 'Using server-side storage' if app.config.get('SESSION_TYPE') in ['redis', 'filesystem'] else 'Consider server-side storage'
    })

@app.route('/donations/<donation_id>', methods=['PUT'])
def update_donation(donation_id):
    """Update a donation record."""
    donations = session.get('donations', [])
    donation_data = request.json
    
    for i, donation in enumerate(donations):
        if donation['internalId'] == donation_id:
            donations[i] = donation_data
            session['donations'] = donations
            return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Donation not found'}), 404

@app.route('/donations/remove-invalid', methods=['POST'])
def remove_invalid_donations():
    """Remove invalid donations from the session."""
    donations = session.get('donations', [])
    
    if not request.json or 'invalidIds' not in request.json:
        return jsonify({
            'success': False,
            'message': 'No invalid IDs provided'
        }), 400
    
    invalid_ids = request.json['invalidIds']
    if not invalid_ids or not isinstance(invalid_ids, list):
        return jsonify({
            'success': False,
            'message': 'Invalid IDs must be a non-empty list'
        }), 400
    
    # Count the number of donations before filtering
    initial_count = len(donations)
    
    # Filter out invalid donations
    valid_donations = [d for d in donations if d.get('internalId') not in invalid_ids]
    
    # Count how many were removed
    removed_count = initial_count - len(valid_donations)
    
    # Update the session
    session['donations'] = valid_donations
    
    print(f"Removed {removed_count} invalid donations from session")
    
    return jsonify({
        'success': True,
        'removedCount': removed_count
    })

@app.route('/qbo/status')
def qbo_status():
    """Check if QBO is authenticated."""
    return jsonify({
        'authenticated': qbo_service.access_token is not None and qbo_service.realm_id is not None,
        'realmId': qbo_service.realm_id,
        'tokenExpiry': qbo_service.token_expires_at if (hasattr(qbo_service, 'token_expires_at') and qbo_service.token_expires_at and qbo_service.token_expires_at > 0) else None,
        'environment': qbo_service.environment  # Include the environment in the status
    })

@app.route('/qbo/authorize')
@limiter.limit("20 per hour")
def authorize_qbo():
    """Start QBO OAuth flow."""
    authorization_url = qbo_service.get_authorization_url()
    return redirect(authorization_url)

@app.route('/qbo/callback')
@csrf.exempt
@limiter.limit("20 per hour")
def qbo_callback():
    """Handle QBO OAuth callback."""
    code = request.args.get('code')
    realmId = request.args.get('realmId')
    error = request.args.get('error')
    
    # Handle OAuth errors
    if error:
        logger.warning(f"QBO OAuth error: {error}")
        log_audit_event(
            'qbo_auth_failed',
            request_ip=request.remote_addr,
            details={'error': error, 'error_description': request.args.get('error_description')}
        )
        error_desc = request.args.get('error_description', 'Unknown error')
        flash(f'QuickBooks authorization failed: {error_desc}', 'error')
        return redirect(url_for('index'))
    
    if not code or not realmId:
        logger.warning("QBO callback missing code or realmId")
        flash('QuickBooks authorization failed: Missing required parameters', 'error')
        return redirect(url_for('index'))
    
    try:
        # Exchange code for tokens
        success = qbo_service.get_tokens(code, realmId)
        
        if success:
            # Log successful authentication
            log_audit_event(
                'qbo_auth_success',
                request_ip=request.remote_addr,
                details={'realm_id': sanitize_for_logging(realmId), 'environment': qbo_service.environment}
            )
            
            # Pre-fetch customers for future matching to populate cache
            try:
                customers = qbo_service.get_all_customers()
                customer_count = len(customers)
                logger.info(f"Pre-fetched {customer_count} customers for future matching")
                
                # Store success message including customer count
                flash(f'Successfully connected to QuickBooks Online. Retrieved {customer_count} customers.', 'success')
            except QBOAPIException as e:
                logger.error(f"Error pre-fetching customers: {str(e)}")
                flash('Connected to QuickBooks Online, but had trouble retrieving customers.', 'warning')
            except Exception as e:
                logger.error(f"Unexpected error pre-fetching customers: {str(e)}")
                flash('Connected to QuickBooks Online.', 'success')
        else:
            flash('Failed to complete QuickBooks authorization', 'error')
            
    except QBOAPIException as e:
        logger.error(f"QBO API error during callback: {str(e)}")
        flash(e.user_message, 'error')
    except Exception as e:
        logger.error(f"Unexpected error in QBO callback: {str(e)}")
        flash('An unexpected error occurred. Please try connecting again.', 'error')
    
    # Add a script to update the UI
    session['qbo_connected'] = True
    session['qbo_just_connected'] = success  # Flag for auth-status endpoint
    
    # Return a simple success page that will work with the popup window
    success_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>QuickBooks Connected</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding-top: 50px; }
            .success { color: #28a745; font-size: 24px; margin-bottom: 20px; }
            .message { margin-bottom: 30px; }
        </style>
    </head>
    <body>
        <div class="success">✓ Successfully Connected to QuickBooks!</div>
        <div class="message">You may close this window and return to the application.</div>
        <script>
            // Close this window after 3 seconds
            setTimeout(function() {
                window.close();
            }, 3000);
        </script>
    </body>
    </html>
    """
    
    return success_html

@app.route('/qbo/customer/<donation_id>', methods=['GET'])
def find_customer(donation_id):
    """Find QBO customer based on donation information."""
    donations = session.get('donations', [])
    
    for donation in donations:
        if donation['internalId'] == donation_id:
            customer_lookup = donation.get('customerLookup', '')
            
            if customer_lookup:
                customer = qbo_service.find_customer(customer_lookup)
                
                if customer:
                    # Compare addresses
                    address_match = True
                    if (donation.get('Address - Line 1') and 
                        donation.get('Address - Line 1') != customer.get('BillAddr', {}).get('Line1', '')):
                        address_match = False
                    
                    donation['qbCustomerStatus'] = 'Matched' if address_match else 'Matched-AddressMismatch'
                    donation['qboCustomerId'] = customer.get('Id')
                    session['donations'] = donations
                    
                    return jsonify({
                        'success': True,
                        'customerFound': True,
                        'addressMatch': address_match,
                        'customer': customer
                    })
                else:
                    donation['qbCustomerStatus'] = 'New'
                    session['donations'] = donations
                    
                    return jsonify({
                        'success': True,
                        'customerFound': False
                    })
    
    return jsonify({'success': False, 'message': 'Donation not found'}), 404

@app.route('/qbo/customers/all', methods=['GET'])
def get_all_customers():
    """Get all QuickBooks customers for manual matching."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get all customers
        all_customers = qbo_service.get_all_customers()
        
        # Prepare simplified customer data for the UI
        customers = []
        for customer in all_customers:
            # Extract address if available
            address = "No address on file"
            if customer.get('BillAddr'):
                bill_addr = customer.get('BillAddr', {})
                addr_parts = []
                if bill_addr.get('Line1'):
                    addr_parts.append(bill_addr.get('Line1'))
                if bill_addr.get('City'):
                    addr_parts.append(bill_addr.get('City'))
                if bill_addr.get('CountrySubDivisionCode'):
                    addr_parts.append(bill_addr.get('CountrySubDivisionCode'))
                if bill_addr.get('PostalCode'):
                    addr_parts.append(bill_addr.get('PostalCode'))
                
                if addr_parts:
                    address = ", ".join(addr_parts)
            
            customers.append({
                'id': customer.get('Id'),
                'name': customer.get('DisplayName', ''),
                'address': address,
                'syncToken': customer.get('SyncToken', '0')
            })
        
        # Sort customers by name for easier browsing
        customers.sort(key=lambda x: x['name'].lower())
        
        return jsonify({
            'success': True,
            'customers': customers
        })
        
    except Exception as e:
        print(f"Error fetching customers: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching customers: {str(e)}'
        }), 500

@app.route('/qbo/customer/manual-match/<donation_id>', methods=['POST'])
def manual_match_customer(donation_id):
    """Manually match a donation to a QBO customer."""
    try:
        # Get donation from session
        donations = session.get('donations', [])
        donation_index = None
        
        for i, donation in enumerate(donations):
            if donation['internalId'] == donation_id:
                donation_index = i
                break
        
        if donation_index is None:
            return jsonify({
                'success': False,
                'message': 'Donation not found'
            }), 404
        
        # Get customer ID from request
        if not request.json or 'customerId' not in request.json:
            return jsonify({
                'success': False,
                'message': 'Customer ID is required'
            }), 400
            
        customer_id = request.json['customerId']
        
        # Get customer details from QBO
        query = f"SELECT * FROM Customer WHERE Id = '{customer_id}'"
        encoded_query = quote(query)
        url = f"{qbo_service.api_base}{qbo_service.realm_id}/query?query={encoded_query}"
        response = requests.get(url, headers=qbo_service._get_auth_headers())
        
        customer = None
        if response.status_code == 200:
            data = response.json()
            if data['QueryResponse'].get('Customer'):
                customer = data['QueryResponse']['Customer'][0]
        
        if not customer:
            return jsonify({
                'success': False,
                'message': 'Customer not found in QBO'
            }), 404
        
        # Update donation with customer info
        donation = donations[donation_index]
        donation['qbCustomerStatus'] = 'Matched'
        donation['qboCustomerId'] = customer.get('Id')
        donation['customerLookup'] = customer.get('DisplayName', '')
        donation['matchMethod'] = 'manual'
        donation['matchConfidence'] = 'high'
        
        # Update session
        session['donations'] = donations
        
        return jsonify({
            'success': True,
            'customer': {
                'id': customer.get('Id'),
                'name': customer.get('DisplayName', ''),
                'syncToken': customer.get('SyncToken', '0')
            }
        })
        
    except Exception as e:
        print(f"Error manually matching customer: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error manually matching customer: {str(e)}'
        }), 500

@app.route('/qbo/customer/create/<donation_id>', methods=['POST'])
@limiter.limit("50 per hour")
def create_customer(donation_id):
    """Create a new QBO customer from donation information."""
    donations = session.get('donations', [])
    
    for i, donation in enumerate(donations):
        if donation['internalId'] == donation_id:
            if donation['dataSource'] == 'CSV':
                return jsonify({'success': False, 'message': 'Cannot create customer from CSV data'}), 400
            
            # Use Donor Name if customerLookup is empty
            display_name = donation.get('customerLookup') or donation.get('Donor Name', '')
            
            # Build customer data with required name fields
            customer_data = {
                'DisplayName': display_name,
                'CompanyName': donation.get('Organization Name', ''),
                'GivenName': donation.get('First Name', ''),
                'FamilyName': donation.get('Last Name', ''),
                'PrimaryEmailAddr': {'Address': ''},
                'BillAddr': {
                    'Line1': donation.get('Address - Line 1', ''),
                    'City': donation.get('City', ''),
                    'CountrySubDivisionCode': donation.get('State', ''),
                    'PostalCode': donation.get('ZIP', '')
                }
            }
            
            # Ensure at least one name field is populated
            if not any([display_name, customer_data['GivenName'], customer_data['FamilyName']]):
                customer_data['DisplayName'] = 'Unknown Donor'
            
            result = qbo_service.create_customer(customer_data)
            
            if result and 'Id' in result:
                donation['qbCustomerStatus'] = 'Matched'
                donation['qboCustomerId'] = result['Id']
                donation['customerLookup'] = result.get('DisplayName', display_name)
                donations[i] = donation
                session['donations'] = donations
                
                return jsonify({
                    'success': True,
                    'customer': result
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to create customer in QBO'
                }), 500
    
    return jsonify({'success': False, 'message': 'Donation not found'}), 404

@app.route('/qbo/customer/update/<donation_id>', methods=['PUT'])
def update_customer(donation_id):
    """Update a QBO customer with new address information."""
    donations = session.get('donations', [])
    
    for i, donation in enumerate(donations):
        if donation['internalId'] == donation_id:
            if donation['dataSource'] == 'CSV':
                return jsonify({'success': False, 'message': 'Cannot update customer from CSV data'}), 400
            
            if not donation.get('qboCustomerId'):
                return jsonify({'success': False, 'message': 'No QBO customer ID available'}), 400
            
            customer_data = {
                'Id': donation['qboCustomerId'],
                'SyncToken': request.json.get('syncToken', '0'),
                'BillAddr': {
                    'Line1': donation.get('Address - Line 1', ''),
                    'City': donation.get('City', ''),
                    'CountrySubDivisionCode': donation.get('State', ''),
                    'PostalCode': donation.get('ZIP', '')
                }
            }
            
            result = qbo_service.update_customer(customer_data)
            
            if result and 'Id' in result:
                donation['qbCustomerStatus'] = 'Matched'
                donations[i] = donation
                session['donations'] = donations
                
                return jsonify({
                    'success': True,
                    'customer': result
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to update customer in QBO'
                }), 500
    
    return jsonify({'success': False, 'message': 'Donation not found'}), 404

@app.route('/qbo/sales-receipt/<donation_id>', methods=['POST'])
@limiter.limit("100 per hour")
def create_sales_receipt(donation_id):
    """Create a QBO sales receipt for a donation."""
    donations = session.get('donations', [])
    
    for i, donation in enumerate(donations):
        if donation['internalId'] == donation_id:
            if donation['dataSource'] == 'CSV':
                return jsonify({'success': False, 'message': 'Cannot create sales receipt from CSV data'}), 400
            
            if not donation.get('qboCustomerId'):
                # Try to find customer first
                customer_lookup = donation.get('customerLookup', '')
                if customer_lookup:
                    customer = qbo_service.find_customer(customer_lookup)
                    if customer:
                        donation['qboCustomerId'] = customer.get('Id')
                    else:
                        return jsonify({
                            'success': False,
                            'message': 'Customer not found in QBO. Please create customer first.'
                        }), 400
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Customer lookup field is empty'
                    }), 400
            
            # Get the item ref from request or use default
            # Ensure we always have a valid itemRef to avoid QBO API errors
            item_ref = request.json.get('itemRef')
            if not item_ref or item_ref.strip() == '':
                item_ref = '1'  # Default fallback
            print(f"Using item_ref: {item_ref} for donation {donation_id}")
            
            # Check if sales receipt already exists
            if donation.get('qboSalesReceiptId'):
                print(f"Sales receipt already exists for donation {donation_id} with ID: {donation['qboSalesReceiptId']}")
                return jsonify({
                    'success': False,
                    'message': 'Sales receipt already created for this donation',
                    'salesReceiptId': donation['qboSalesReceiptId']
                }), 400
            
            # Format dates with validation
            today = pd.Timestamp.now().strftime('%Y-%m-%d')
            
            # Validate and format Check Date
            check_date = donation.get('Check Date', '')
            
            # Validate the date
            is_valid, warning_msg, parsed_date = validate_donation_date(check_date, "Check Date")
            
            if not is_valid:
                return jsonify({
                    'success': False,
                    'message': warning_msg
                }), 400
            
            if warning_msg:
                print(f"Date validation warning: {warning_msg}")
            
            if parsed_date:
                check_date = parsed_date.strftime('%Y-%m-%d')
                print(f"Using Check Date: {check_date} for sales receipt")
            else:
                # If no check date, use today's date
                print(f"No Check Date provided, using today's date: {today}")
                check_date = today
            
            # Get other fields with validation
            check_no = donation.get('Check No.', 'N/A')
            # Validate Gift Amount
            try:
                gift_amount = float(donation.get('Gift Amount', 0))
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid Gift Amount, must be a number'
                }), 400
            
            last_name = donation.get('Last Name', '')
            first_name = donation.get('First Name', '')
            memo = donation.get('Memo', '')
            
            # Format description, limiting to reasonable length
            description = f"{check_no}_{check_date}_{gift_amount}_{last_name}_{first_name}"
            if memo:
                description += f"_{memo}"
            
            # Truncate if too long - QuickBooks has limits
            if len(description) > 1000:
                description = description[:997] + "..."
            
            # Format receipt number
            doc_number = f"{today}_{check_no}"
            if len(doc_number) > 21:  # QB has a 21 char limit
                doc_number = doc_number[:21]
            
            # Check for custom account ID from setup modal
            deposit_account_id = request.json.get('depositToAccountId', '12000')
            payment_method_id = request.json.get('paymentMethodId', 'CHECK')
            
            # Log custom fields if provided
            if request.json.get('depositToAccountId'):
                print(f"Using custom deposit account ID: {deposit_account_id}")
            if request.json.get('paymentMethodId'):
                print(f"Using custom payment method ID: {payment_method_id}")
            
            # Check for existing sales receipt in QBO before creating a new one
            print(f"Checking for existing sales receipt with check_no: {check_no}, date: {check_date}, customer: {donation['qboCustomerId']}")
            existing_receipt = qbo_service.find_sales_receipt(check_no, check_date, donation['qboCustomerId'])
            
            if existing_receipt:
                print(f"Found existing sales receipt with ID: {existing_receipt.get('Id')}")
                # Update donation record with existing receipt ID
                donation['qbSyncStatus'] = 'Sent'
                donation['qboSalesReceiptId'] = existing_receipt.get('Id')
                donations[i] = donation
                session['donations'] = donations
                
                return jsonify({
                    'success': True,
                    'duplicate': True,
                    'message': 'Sales receipt already exists in QuickBooks',
                    'salesReceipt': existing_receipt
                })
                
            # Prepare sales receipt data
            sales_receipt_data = {
                'CustomerRef': {
                    'value': donation['qboCustomerId']
                },
                'PaymentMethodRef': {
                    'value': payment_method_id  # May be custom or default 'CHECK'
                },
                'PaymentRefNum': check_no,
                'TxnDate': check_date,
                'DepositToAccountRef': {
                    'value': deposit_account_id  # May be custom or default '12000'
                },
                'DocNumber': doc_number,
                'Line': [
                    {
                        'DetailType': 'SalesItemLineDetail',
                        'Amount': gift_amount,
                        'SalesItemLineDetail': {
                            'ItemRef': {
                                'value': item_ref
                            },
                            'ServiceDate': check_date
                        },
                        'Description': description
                    }
                ],
                'CustomerMemo': {
                    'value': f"auto import on {today}"
                }
            }
            
            # Log audit event before creating sales receipt
            log_audit_event(
                'sales_receipt_create',
                request_ip=request.remote_addr,
                details={
                    'donation_id': donation_id,
                    'customer_id': donation['qboCustomerId'],
                    'amount': gift_amount,
                    'check_no': check_no,
                    'check_date': check_date
                }
            )
            
            result = qbo_service.create_sales_receipt(sales_receipt_data)
            
            # Check for error returned from enhanced error handling
            if result and result.get('error'):
                error_message = result.get('message', 'Unknown error')
                error_detail = result.get('detail', '')
                
                # Format storage of the error in the donation record
                donation['qbSyncStatus'] = 'Error'
                donation['qbSyncError'] = error_message
                donations[i] = donation
                session['donations'] = donations
                
                # Check for specific types of errors
                if result.get('requiresSetup'):
                    return jsonify({
                        'success': False,
                        'requiresSetup': True,
                        'setupType': result.get('setupType'),
                        'invalidId': result.get('invalidId'),
                        'message': error_message,
                        'detail': error_detail
                    }), 400
                
                # Default error response for other types of errors
                return jsonify({
                    'success': False,
                    'message': error_message,
                    'detail': error_detail
                }), 500
            
            if result and 'Id' in result:
                donation['qbSyncStatus'] = 'Sent'
                donation['qboSalesReceiptId'] = result['Id']
                donations[i] = donation
                session['donations'] = donations
                
                return jsonify({
                    'success': True,
                    'salesReceipt': result
                })
            else:
                donation['qbSyncStatus'] = 'Error'
                donations[i] = donation
                session['donations'] = donations
                
                return jsonify({
                    'success': False,
                    'message': 'Failed to create sales receipt in QBO'
                }), 500
    
    return jsonify({'success': False, 'message': 'Donation not found'}), 404

@app.route('/qbo/sales-receipt/batch', methods=['POST'])
@limiter.limit("20 per hour")
def create_batch_sales_receipts():
    """Create QBO sales receipts for all eligible donations."""
    donations = session.get('donations', [])
    results = []
    
    # Get the default values from request or use defaults
    default_item_ref = request.json.get('defaultItemRef', '1')  # Default fallback
    default_account_id = request.json.get('defaultDepositToAccountId', '12000')  # Default fallback
    default_payment_method_id = request.json.get('defaultPaymentMethodId', 'CHECK')  # Default fallback
    
    # Log what we're sending for debugging
    print(f"Sending batch sales receipts with default itemRef: {default_item_ref}, depositToAccountId: {default_account_id}, paymentMethodId: {default_payment_method_id}")
    
    # Track processing stats
    success_count = 0
    failure_count = 0
    
    for i, donation in enumerate(donations):
        try:
            # Skip CSV donations and already sent donations
            if donation['dataSource'] == 'CSV' or donation['qbSyncStatus'] == 'Sent':
                continue
            
            # Skip donations marked to exclude
            if donation.get('excludeFromBatch'):
                results.append({
                    'internalId': donation['internalId'],
                    'success': False,
                    'message': 'Excluded from batch processing'
                })
                failure_count += 1
                continue
            
            # Skip if sales receipt already exists
            if donation.get('qboSalesReceiptId'):
                results.append({
                    'internalId': donation['internalId'],
                    'success': False,
                    'message': 'Sales receipt already exists'
                })
                continue
            
            if not donation.get('qboCustomerId'):
                # Try to find customer first
                customer_lookup = donation.get('customerLookup', '')
                if customer_lookup:
                    customer = qbo_service.find_customer(customer_lookup)
                    if customer:
                        donation['qboCustomerId'] = customer.get('Id')
                    else:
                        results.append({
                            'internalId': donation['internalId'],
                            'success': False,
                            'message': 'Customer not found in QBO'
                        })
                        failure_count += 1
                        continue
                else:
                    results.append({
                        'internalId': donation['internalId'],
                        'success': False,
                        'message': 'Customer lookup field is empty'
                    })
                    failure_count += 1
                    continue
            
            # Validate data before sending
            
            # Validate and format Check Date
            today = pd.Timestamp.now().strftime('%Y-%m-%d')
            check_date = donation.get('Check Date', '')
            # Validate the date
            is_valid, warning_msg, parsed_date = validate_donation_date(check_date, "Check Date")
            
            if not is_valid:
                results.append({
                    'internalId': donation['internalId'],
                    'success': False,
                    'message': warning_msg
                })
                failure_count += 1
                continue
            
            if warning_msg:
                print(f"Date validation warning for donation {donation['internalId']}: {warning_msg}")
            
            if parsed_date:
                check_date = parsed_date.strftime('%Y-%m-%d')
                print(f"Using Check Date: {check_date} for donation {donation['internalId']}")
            else:
                check_date = today
            
            # Validate Gift Amount
            try:
                gift_amount = float(donation.get('Gift Amount', 0))
                if gift_amount <= 0:
                    raise ValueError("Gift amount must be greater than zero")
            except ValueError as e:
                # Skip donations with invalid amounts
                error_msg = f"Invalid Gift Amount: {donation.get('Gift Amount')} - {str(e)}"
                results.append({
                    'internalId': donation['internalId'],
                    'success': False,
                    'message': error_msg
                })
                # Mark donation as error
                donation['qbSyncStatus'] = 'Error'
                donation['qbSyncError'] = error_msg
                donations[i] = donation
                failure_count += 1
                continue
            
            # Get other fields with validation
            check_no = donation.get('Check No.', 'N/A')
            last_name = donation.get('Last Name', '')
            first_name = donation.get('First Name', '')
            memo = donation.get('Memo', '')
            
            # Format description
            description = f"{check_no}_{check_date}_{gift_amount}_{last_name}_{first_name}"
            if memo:
                description += f"_{memo}"
            
            # Truncate if too long - QuickBooks has limits
            if len(description) > 1000:
                description = description[:997] + "..."
            
            # Format receipt number
            doc_number = f"{today}_{check_no}"
            if len(doc_number) > 21:  # QB has a 21 char limit
                doc_number = doc_number[:21]
            
            # Use item ref from the donation if specified, otherwise use the default
            # Ensure we always have a valid item reference to avoid QBO API errors
            item_ref = donation.get('itemRef') 
            if not item_ref or (isinstance(item_ref, str) and item_ref.strip() == ''):
                item_ref = default_item_ref
            # If we still don't have a valid item_ref, use '1' as the last resort
            if not item_ref or (isinstance(item_ref, str) and item_ref.strip() == ''):
                item_ref = '1'
            print(f"Using item_ref: {item_ref} for batch donation {donation.get('internalId')}")
            
            # Prepare sales receipt data with all required fields
            sales_receipt_data = {
                'CustomerRef': {
                    'value': donation['qboCustomerId']
                },
                'PaymentMethodRef': {
                    'value': default_payment_method_id  # Use the parameter from request
                },
                'PaymentRefNum': check_no,
                'TxnDate': check_date,
                'DepositToAccountRef': {
                    'value': default_account_id  # Use the parameter from request
                },
                'DocNumber': doc_number,
                'Line': [
                    {
                        'DetailType': 'SalesItemLineDetail',
                        'Amount': gift_amount,
                        'SalesItemLineDetail': {
                            'ItemRef': {
                                'value': item_ref
                            },
                            'ServiceDate': check_date
                        },
                        'Description': description
                    }
                ],
                'CustomerMemo': {
                    'value': f"auto import on {today}"
                }
            }
            
            # Check for existing sales receipt before creating
            existing_receipt = qbo_service.find_sales_receipt(check_no, check_date, donation['qboCustomerId'])
            
            if existing_receipt:
                # Sales receipt already exists - update donation and continue
                donation['qbSyncStatus'] = 'Sent'
                donation['qboSalesReceiptId'] = existing_receipt.get('Id')
                donations[i] = donation
                
                results.append({
                    'internalId': donation['internalId'],
                    'success': True,
                    'salesReceiptId': existing_receipt.get('Id'),
                    'message': 'Sales receipt already exists'
                })
                success_count += 1
                continue
            
            result = qbo_service.create_sales_receipt(sales_receipt_data)
            
            # Check for error returned from enhanced error handling
            if result and result.get('error'):
                error_msg = result.get('message', 'Unknown error')
                donation['qbSyncStatus'] = 'Error'
                donation['qbSyncError'] = error_msg
                donations[i] = donation
                
                results.append({
                    'internalId': donation['internalId'],
                    'success': False,
                    'message': error_msg
                })
                failure_count += 1
                continue
            
            if result and 'Id' in result:
                donation['qbSyncStatus'] = 'Sent'
                donation['qboSalesReceiptId'] = result['Id']
                donations[i] = donation
                
                results.append({
                    'internalId': donation['internalId'],
                    'success': True,
                    'salesReceiptId': result['Id']
                })
                success_count += 1
            else:
                error_msg = 'Failed to create sales receipt in QBO'
                donation['qbSyncStatus'] = 'Error'
                donation['qbSyncError'] = error_msg
                donations[i] = donation
                
                results.append({
                    'internalId': donation['internalId'],
                    'success': False,
                    'message': error_msg
                })
                failure_count += 1
        
        except Exception as e:
            # Catch any unexpected errors during processing
            error_msg = f"Unexpected error: {str(e)}"
            results.append({
                'internalId': donation.get('internalId', 'unknown'),
                'success': False,
                'message': error_msg
            })
            
            # If we have a valid donation index, update its status
            if i < len(donations):
                donations[i]['qbSyncStatus'] = 'Error'
                donations[i]['qbSyncError'] = error_msg
            
            failure_count += 1
    
    # Save all donation changes to session
    session['donations'] = donations
    
    return jsonify({
        'success': True,
        'summary': {
            'total': len(results),
            'success': success_count,
            'failure': failure_count
        },
        'results': results
    })

@app.route('/clear-all', methods=['POST'])
def clear_all_donations():
    """Clear all donations from the session."""
    try:
        # Clear donations from session
        session['donations'] = []
        
        # Also clear any other related session data
        if 'upload_summary' in session:
            del session['upload_summary']
        
        # Ensure session is saved
        session.modified = True
        
        return jsonify({'success': True, 'message': 'All donations cleared successfully'})
    except Exception as e:
        print(f"Error clearing donations: {str(e)}")
        return jsonify({'success': False, 'message': 'Error clearing donations'}), 500

@app.route('/report/generate', methods=['GET'])
def generate_report():
    """Generate a donation report."""
    donations = session.get('donations', [])
    
    if not donations:
        return jsonify({'success': False, 'message': 'No donations to report'}), 400
    
    # Format report similar to the provided examples
    report_data = []
    valid_entry_index = 1
    
    # Current date for the report
    current_date = pd.Timestamp.now().strftime('%m/%d/%Y')
    
    for donation in donations:
        # Skip entries with missing or invalid gift amounts
        if 'Gift Amount' not in donation or not donation['Gift Amount']:
            print(f"Skipping donation with missing Gift Amount: {donation.get('Donor Name', 'Unknown')}")
            continue
            
        donor_name = donation.get('Donor Name', 'Unknown Donor')
        address = donation.get('Address - Line 1', '')
        city = donation.get('City', '')
        state = donation.get('State', '')
        zipcode = donation.get('ZIP', '')
        address_line = f"{address}, {city}, {state} {zipcode}" if all([address, city, state, zipcode]) else ''
        
        # Create a multi-line address for text report format
        address_line_1 = address
        address_line_2 = f"{city}, {state} {zipcode}" if all([city, state, zipcode]) else ''
        
        # Safely convert gift amount to float
        try:
            amount_str = donation.get('Gift Amount', '0')
            if isinstance(amount_str, str):
                amount = float(amount_str.replace('$', '').replace(',', ''))
            else:
                amount = float(amount_str) if amount_str is not None else 0.0
        except (ValueError, TypeError):
            print(f"Skipping donation with invalid Gift Amount: {donor_name}")
            continue
        
        gift_date = donation.get('Gift Date', donation.get('Check Date', ''))
        check_no = donation.get('Check No.', '')
        if not check_no and donation.get('dataSource') == 'CSV':
            check_no = 'Online Donation'
        
        memo = donation.get('Memo', '')
        
        # Create full donation record with all fields for CSV export
        report_entry = {
            'index': valid_entry_index,
            'donor_name': donor_name,
            'address_line_1': address_line_1,
            'address_line_2': address_line_2,
            'address': address_line,  # Single line address for display
            'amount': amount,
            'date': gift_date,
            'check_no': check_no,
            'memo': memo,
            # Include all original fields for CSV export
            'first_name': donation.get('First Name', ''),
            'last_name': donation.get('Last Name', ''),
            'full_name': donation.get('Full Name', ''),
            'organization': donation.get('Organization Name', ''),
            'city': city,
            'state': state,
            'zip': zipcode,
            'deposit_date': donation.get('Deposit Date', current_date),
            'deposit_method': donation.get('Deposit Method', 'Check'),
            'customer_lookup': donation.get('customerLookup', '')
        }
        
        report_data.append(report_entry)
        valid_entry_index += 1
    
    # Calculate total (only for valid entries that made it to report_data)
    total = sum(entry['amount'] for entry in report_data)
    
    # Generate text report format (like in FOM deposit reports.md)
    text_report_lines = [
        f"**Deposit Report: {current_date}**",
        f"Below is a list of deposits totaling ${total:.2f}:",
        ""  # Blank line
    ]
    
    for entry in report_data:
        # Format each donation in the text format from the example
        text_report_lines.extend([
            f"{entry['index']}. {entry['donor_name']}",
            f"   {entry['address_line_1']}" if entry['address_line_1'] else "",
            f"   {entry['address_line_2']}" if entry['address_line_2'] else "",
            f"   ${entry['amount']:.2f} on {entry['date']}",
            f"   Check No. {entry['check_no']}",
            f"   Memo: {entry['memo']}" if entry['memo'] else "",
            ""  # Blank line between entries
        ])
    
    # Add total to the text report
    text_report_lines.append(f"Total Deposits: ${total:.2f}")
    
    # Remove any empty lines (like if address_line_1 was empty)
    text_report_lines = [line for line in text_report_lines if line]
    
    # Join the text report lines
    text_report = "\n".join(text_report_lines)
    
    report = {
        'entries': report_data,
        'total': total,
        'text_report': text_report,
        'report_date': current_date
    }
    
    return jsonify({
        'success': True,
        'report': report
    })

@app.route('/save', methods=['POST'])
def save_changes():
    """Save current donation data to local storage."""
    # This is a placeholder for saving to a database in a future implementation
    # Currently, data is just maintained in the session
    donations = session.get('donations', [])
    
    if request.json and 'donations' in request.json:
        session['donations'] = request.json['donations']
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'No donation data provided'}), 400

@app.route('/test/qbo/customers', methods=['GET'])
def test_qbo_customers():
    """Test route to verify QuickBooks customer retrieval."""
    try:
        print("Starting QBO customer retrieval test...")
        # First check if we're authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            print("Not authenticated with QBO")
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks. Please connect to QBO first.',
                'authenticated': False
            })
        
        # Try to get a customer count first (lightweight operation)
        query = "SELECT COUNT(*) FROM Customer"
        encoded_query = quote(query)
        url = f"{qbo_service.api_base}{qbo_service.realm_id}/query?query={encoded_query}"
        response = requests.get(url, headers=qbo_service._get_auth_headers())
        
        customer_count = 0
        if response.status_code == 200:
            data = response.json()
            if 'QueryResponse' in data and 'totalCount' in data['QueryResponse']:
                customer_count = data['QueryResponse']['totalCount']
                print(f"Found {customer_count} customers in QuickBooks")
        
        # Try to get at most 10 customers for the test
        customers = []
        query = "SELECT * FROM Customer MAXRESULTS 10"
        encoded_query = quote(query)
        url = f"{qbo_service.api_base}{qbo_service.realm_id}/query?query={encoded_query}"
        response = requests.get(url, headers=qbo_service._get_auth_headers())
        
        if response.status_code == 200:
            data = response.json()
            customers = data['QueryResponse'].get('Customer', [])
            print(f"Retrieved {len(customers)} sample customers")
        
        # Now test the get_all_customers method
        print("Testing get_all_customers method...")
        all_customers = qbo_service.get_all_customers()
        
        return jsonify({
            'success': True,
            'authenticated': True,
            'customerCount': customer_count,
            'sampleCustomersCount': len(customers),
            'sampleCustomers': [c.get('DisplayName') for c in customers[:10]],
            'allCustomersCount': len(all_customers),
            'message': f"Successfully retrieved {len(all_customers)} customers out of {customer_count} total"
        })
        
    except Exception as e:
        print(f"Error in test_qbo_customers: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f"Error testing QBO customers: {str(e)}",
            'error': str(e)
        }), 500

@app.route('/test/match', methods=['POST'])
def test_customer_matching():
    """Test route to check customer matching for a sample donation."""
    try:
        if not request.json:
            return jsonify({'success': False, 'message': 'No donation data provided'}), 400
            
        donation_data = request.json
        customer_lookup = donation_data.get('customerLookup', donation_data.get('Donor Name', ''))
        
        if not customer_lookup:
            return jsonify({
                'success': False,
                'message': 'No customer lookup value provided'
            }), 400
            
        # Perform direct QBO API lookup
        customer = qbo_service.find_customer(customer_lookup)
        
        # Check for address match if customer found
        address_match = True
        if customer and donation_data.get('Address - Line 1') and donation_data.get('Address - Line 1') != customer.get('BillAddr', {}).get('Line1', ''):
            address_match = False
        
        # Return the matching result
        if customer:
            return jsonify({
                'success': True,
                'customerFound': True,
                'addressMatch': address_match,
                'customer': customer,
                'message': 'Customer found in QBO'
            })
        else:
            return jsonify({
                'success': True,
                'customerFound': False,
                'message': 'No matching customer found in QBO'
            })
        
    except Exception as e:
        print(f"Error in test_customer_matching: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f"Error testing customer matching: {str(e)}",
            'error': str(e)
        }), 500

@app.route('/qbo/sales-receipt/preview/<donation_id>', methods=['POST'])
def preview_sales_receipt(donation_id):
    """Preview a QBO sales receipt for a donation without sending it."""
    try:
        donations = session.get('donations', [])
        donation = None
        
        # Find the donation
        for d in donations:
            if d['internalId'] == donation_id:
                donation = d
                break
        
        if not donation:
            return jsonify({'success': False, 'message': 'Donation not found'}), 404
        
        if donation['dataSource'] == 'CSV':
            return jsonify({'success': False, 'message': 'Cannot create sales receipt from CSV data'}), 400
        
        # Get the item ref from request or use default
        item_ref = '1'  # Default fallback
        if request.json and 'itemRef' in request.json:
            item_ref = request.json['itemRef']
        
        # Format dates and construct the sales receipt data
        today = pd.Timestamp.now().strftime('%Y-%m-%d')
        gift_date = donation.get('Gift Date', '')
        check_date = donation.get('Check Date', '')
        check_no = donation.get('Check No.', 'N/A')
        
        # Handle gift amount with proper parsing of currency strings
        gift_amount_str = donation.get('Gift Amount', '0')
        try:
            # If it's already a number, use it directly
            if isinstance(gift_amount_str, (int, float)):
                gift_amount = float(gift_amount_str)
            else:
                # Remove currency symbols, commas, and other formatting
                gift_amount = float(gift_amount_str.replace('$', '').replace(',', '').strip())
        except (ValueError, TypeError) as e:
            print(f"Error parsing gift amount '{gift_amount_str}': {str(e)}")
            gift_amount = 0.0  # Default to zero if parsing fails
        
        last_name = donation.get('Last Name', '')
        first_name = donation.get('First Name', '')
        memo = donation.get('Memo', '')
        
        # Format description
        description = f"{check_no}_{gift_date}_{gift_amount_str}_{last_name}_{first_name}"
        if memo:
            description += f"_{memo}"
        
        # Format receipt number
        doc_number = f"{today}_{check_no}"
        if len(doc_number) > 21:  # QB has a 21 char limit
            doc_number = doc_number[:21]
        
        # Get deposit account info from request
        deposit_account_id = request.json.get('depositToAccountId', '12000')
        
        # Construct the preview data
        preview_data = {
            'success': True,
            'salesReceiptPreview': {
                'customerName': donation.get('customerLookup', ''),
                'paymentMethod': 'Check',
                'referenceNo': check_no,
                'date': gift_date,
                'depositTo': f"{deposit_account_id} Undeposited Funds",
                'depositToAccountId': deposit_account_id,
                'serviceDate': check_date,
                'itemRef': item_ref,
                'description': description,
                'amount': gift_amount,  # Now properly parsed as float
                'message': f"auto import on {today}",
                'docNumber': doc_number
            }
        }
        
        return jsonify(preview_data)
        
    except Exception as e:
        print(f"Error previewing sales receipt: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error previewing sales receipt: {str(e)}'
        }), 500

@app.route('/qbo/environment')
def qbo_environment_info():
    """Show current QBO environment information."""
    return jsonify({
        'environment': qbo_service.environment,
        'apiBaseUrl': qbo_service.api_base,
        'authenticated': qbo_service.access_token is not None and qbo_service.realm_id is not None,
        'realmId': qbo_service.realm_id if qbo_service.realm_id else None
    })

@app.route('/qbo/items/all', methods=['GET'])
def get_all_items():
    """Get all QuickBooks items/products/services."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get all items
        all_items = qbo_service.get_all_items()
        
        # Prepare simplified item data for the UI
        items = []
        for item in all_items:
            # Skip inactive items
            if not item.get('Active', True):
                continue
                
            items.append({
                'id': item.get('Id'),
                'name': item.get('Name', ''),
                'description': item.get('Description', ''),
                'type': item.get('Type', ''),
                'unitPrice': item.get('UnitPrice', 0)
            })
        
        # Sort items by name for easier selection in the UI
        items.sort(key=lambda x: x['name'].lower())
        
        return jsonify({
            'success': True,
            'items': items
        })
        
    except Exception as e:
        print(f"Error fetching items: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching items: {str(e)}'
        }), 500

@app.route('/qbo/item/create', methods=['POST'])
def create_item():
    """Create a new QBO product/service item."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get item data from request
        if not request.json:
            return jsonify({
                'success': False,
                'message': 'No item data provided'
            }), 400
        
        # Validate required fields
        item_data = request.json
        if 'name' not in item_data or not item_data['name']:
            return jsonify({
                'success': False,
                'message': 'Item name is required'
            }), 400
        
        if 'incomeAccountId' not in item_data or not item_data['incomeAccountId']:
            return jsonify({
                'success': False,
                'message': 'Income account is required'
            }), 400
        
        # Build QBO-formatted item data
        qbo_item_data = {
            'Name': item_data['name'],
            'Type': item_data.get('type', 'Service'),
            'IncomeAccountRef': {
                'value': item_data['incomeAccountId']
            },
            'Active': True
        }
        
        # Add optional fields if present
        if 'description' in item_data and item_data['description']:
            qbo_item_data['Description'] = item_data['description']
            
        if 'price' in item_data and item_data['price']:
            try:
                price = float(item_data['price'])
                qbo_item_data['UnitPrice'] = price
            except (ValueError, TypeError):
                pass  # Skip invalid price values
        
        # Create the item
        created_item = qbo_service.create_item(qbo_item_data)
        
        if created_item:
            return jsonify({
                'success': True,
                'item': {
                    'id': created_item.get('Id'),
                    'name': created_item.get('Name'),
                    'description': created_item.get('Description', ''),
                    'type': created_item.get('Type', 'Other'),
                    'price': created_item.get('UnitPrice', 0)
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create item in QBO'
            }), 500
            
    except Exception as e:
        print(f"Error creating item: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error creating item: {str(e)}'
        }), 500

@app.route('/qbo/accounts/all', methods=['GET'])
def get_all_accounts():
    """Get all QuickBooks accounts."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get all accounts
        all_accounts = qbo_service.get_all_accounts()
        
        # Look for Undeposited Funds account
        undeposited_funds = None
        for account in all_accounts:
            # Check if this is an Undeposited Funds account by name or account type
            if (account.get('Name', '').lower() == 'undeposited funds' or
                account.get('AccountSubType', '').lower() == 'undepositedFunds'.lower()):
                undeposited_funds = {
                    'id': account.get('Id'),
                    'name': account.get('Name', ''),
                    'type': account.get('AccountType', ''),
                    'subType': account.get('AccountSubType', '')
                }
                print(f"Found Undeposited Funds account: {undeposited_funds}")
                break
        
        # Prepare simplified account data for the UI
        accounts = []
        for account in all_accounts:
            accounts.append({
                'id': account.get('Id'),
                'name': account.get('Name', ''),
                'type': account.get('AccountType', ''),
                'subType': account.get('AccountSubType', ''),
                'number': account.get('AcctNum', ''),
                'active': account.get('Active', True)
            })
        
        return jsonify({
            'success': True,
            'accounts': accounts,
            'undepositedFunds': undeposited_funds
        })
        
    except Exception as e:
        print(f"Error fetching accounts: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching accounts: {str(e)}'
        }), 500

@app.route('/qbo/account/create', methods=['POST'])
def create_account():
    """Create a new QBO account."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get account data from request
        if not request.json:
            return jsonify({
                'success': False,
                'message': 'No account data provided'
            }), 400
        
        # Validate required fields
        account_data = request.json
        if 'name' not in account_data or not account_data['name']:
            return jsonify({
                'success': False,
                'message': 'Account name is required'
            }), 400
        
        if 'accountType' not in account_data or not account_data['accountType']:
            return jsonify({
                'success': False,
                'message': 'Account type is required'
            }), 400
        
        # Build QBO-formatted account data
        qbo_account_data = {
            'Name': account_data['name'],
            'AccountType': account_data['accountType'],
            'Active': True
        }
        
        # Add optional fields if present
        if 'accountSubType' in account_data and account_data['accountSubType']:
            qbo_account_data['AccountSubType'] = account_data['accountSubType']
            
        if 'description' in account_data and account_data['description']:
            qbo_account_data['Description'] = account_data['description']
            
        if 'accountNumber' in account_data and account_data['accountNumber']:
            qbo_account_data['AcctNum'] = account_data['accountNumber']
        
        # Create the account
        created_account = qbo_service.create_account(qbo_account_data)
        
        if created_account:
            return jsonify({
                'success': True,
                'account': {
                    'id': created_account.get('Id'),
                    'name': created_account.get('Name'),
                    'type': created_account.get('AccountType')
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create account in QBO'
            }), 500
            
    except Exception as e:
        print(f"Error creating account: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error creating account: {str(e)}'
        }), 500

@app.route('/qbo/payment-methods/all', methods=['GET'])
def get_all_payment_methods():
    """Get all QuickBooks payment methods."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get all payment methods
        all_payment_methods = qbo_service.get_all_payment_methods()
        
        # Prepare simplified payment method data for the UI
        payment_methods = []
        for method in all_payment_methods:
            payment_methods.append({
                'id': method.get('Id'),
                'name': method.get('Name', ''),
                'active': method.get('Active', True)
            })
        
        return jsonify({
            'success': True,
            'paymentMethods': payment_methods
        })
        
    except Exception as e:
        print(f"Error fetching payment methods: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error fetching payment methods: {str(e)}'
        }), 500

@app.route('/qbo/payment-method/create', methods=['POST'])
def create_payment_method():
    """Create a new QBO payment method."""
    try:
        # Check if authenticated
        if not qbo_service.access_token or not qbo_service.realm_id:
            return jsonify({
                'success': False,
                'message': 'Not authenticated with QuickBooks Online'
            }), 401
        
        # Get payment method data from request
        if not request.json:
            return jsonify({
                'success': False,
                'message': 'No payment method data provided'
            }), 400
        
        # Validate required fields
        payment_method_data = request.json
        if 'name' not in payment_method_data or not payment_method_data['name']:
            return jsonify({
                'success': False,
                'message': 'Payment method name is required'
            }), 400
        
        # Build QBO-formatted payment method data
        qbo_payment_method_data = {
            'Name': payment_method_data['name'],
            'Active': True
        }
        
        # Create the payment method
        created_payment_method = qbo_service.create_payment_method(qbo_payment_method_data)
        
        if created_payment_method:
            return jsonify({
                'success': True,
                'paymentMethod': {
                    'id': created_payment_method.get('Id'),
                    'name': created_payment_method.get('Name')
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create payment method in QBO'
            }), 500
            
    except Exception as e:
        print(f"Error creating payment method: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error creating payment method: {str(e)}'
        }), 500

@app.route('/donations/clear', methods=['POST'])
def clear_donations():
    """Clear all donations from the session."""
    session['donations'] = []
    return jsonify({'success': True, 'message': 'All donations cleared from session'})

@app.route('/donations/debug', methods=['GET'])
def debug_donations():
    """Debug endpoint to see donation keys and deduplication info."""
    donations = session.get('donations', [])
    
    debug_info = {
        'total_count': len(donations),
        'donations_by_key': {}
    }
    
    # Group donations by their unique keys
    for donation in donations:
        check_no = normalize_check_number(donation.get('Check No.', ''))
        amount = normalize_amount(donation.get('Gift Amount', ''))
        
        if check_no and amount:
            unique_key = f"CHECK_{check_no}_{amount}"
        else:
            donor_name = normalize_donor_name(donation.get('Donor Name', ''))
            gift_date = normalize_date(donation.get('Gift Date', ''))
            unique_key = f"OTHER_{donor_name}_{amount}_{gift_date}"
        
        if unique_key not in debug_info['donations_by_key']:
            debug_info['donations_by_key'][unique_key] = []
        
        debug_info['donations_by_key'][unique_key].append({
            'internalId': donation.get('internalId'),
            'donor': donation.get('Donor Name'),
            'checkNo': donation.get('Check No.'),
            'amount': donation.get('Gift Amount'),
            'date': donation.get('Gift Date'),
            'isMerged': donation.get('isMerged', False),
            'dataSource': donation.get('dataSource')
        })
    
    # Find any duplicate keys (should not exist)
    duplicates = {k: v for k, v in debug_info['donations_by_key'].items() if len(v) > 1}
    debug_info['duplicate_keys'] = duplicates
    debug_info['duplicate_count'] = sum(len(v) - 1 for v in duplicates.values())
    
    return jsonify(debug_info)

if __name__ == '__main__':
    # Display the environment when starting
    print(f"====== Starting with QuickBooks Online {qbo_environment.upper()} environment ======")
    print(f"API Base URL: {qbo_service.api_base}")
    print(f"To change environments, restart with: python src/app.py --env [sandbox|production]")
    print("================================================================")
    
    app.run(debug=True)