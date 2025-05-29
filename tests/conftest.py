"""Pytest configuration and fixtures for all tests."""

import os
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set test environment variables before any imports
os.environ["FLASK_ENV"] = "testing"
os.environ["FLASK_SECRET_KEY"] = "test-secret-key"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["QBO_CLIENT_ID"] = "test-client-id"
os.environ["QBO_CLIENT_SECRET"] = "test-client-secret"
os.environ["QBO_REDIRECT_URI"] = "http://localhost/callback"
os.environ["MAX_FILES_PER_UPLOAD"] = "20"


# Mock Redis before importing the app
class MockRedis:
    """Mock Redis client for testing."""

    def __init__(self, *args, **kwargs):
        self.data = {}

    def ping(self):
        return True

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, **kwargs):
        # Handle both positional and keyword arguments
        # Flask-Session may call with name=key, value=value
        if "name" in kwargs:
            key = kwargs["name"]
        if "value" in kwargs:
            value = kwargs["value"]
        self.data[key] = value
        return True

    def setex(self, key, time, value, **kwargs):
        self.data[key] = value
        return True

    def delete(self, key):
        if key in self.data:
            del self.data[key]
        return True

    def exists(self, key):
        return key in self.data

    def info(self):
        return {"redis_version": "test", "used_memory_human": "1M"}


# Patch Redis globally for all tests
redis_patch = patch("redis.from_url", return_value=MockRedis())
redis_patch.start()
redis_class_patch = patch("redis.Redis", MockRedis)
redis_class_patch.start()


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    # Import here after Redis is mocked
    from src.app import app as flask_app

    # Configure app for testing
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for tests
    flask_app.config["SESSION_TYPE"] = "filesystem"

    # Create a temporary directory for session files
    with tempfile.TemporaryDirectory() as temp_dir:
        flask_app.config["SESSION_FILE_DIR"] = temp_dir

        # Create test upload folder
        upload_folder = os.path.join(temp_dir, "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        flask_app.config["UPLOAD_FOLDER"] = upload_folder

        yield flask_app


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test runner for the Flask application."""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers():
    """Provide headers with CSRF token for authenticated requests."""
    return {"X-CSRFToken": "test-csrf-token", "Content-Type": "application/json"}


@pytest.fixture
def mock_qbo_service():
    """Mock QBO service for tests."""
    mock_service = Mock()
    mock_service.access_token = "test-token"
    mock_service.refresh_token = "test-refresh-token"
    mock_service.realm_id = "test-realm-id"
    mock_service.token_expires_at = 1234567890
    mock_service.is_token_valid.return_value = True
    mock_service.get_authorization_url.return_value = "https://test.intuit.com/auth"
    mock_service.get_tokens.return_value = True
    mock_service.refresh_access_token.return_value = True
    mock_service.find_customer.return_value = None
    mock_service.create_customer.return_value = {"Id": "123", "DisplayName": "Test Customer"}
    mock_service.create_sales_receipt.return_value = {"Id": "456", "DocNumber": "1001"}
    return mock_service


@pytest.fixture
def mock_gemini_service():
    """Mock Gemini service for tests."""
    mock_service = Mock()
    mock_service.extract_donation_data.return_value = {
        "Donor Name": "Test Donor",
        "Gift Amount": "100.00",
        "Check No.": "1234",
        "Check Date": "2024-01-01",
    }
    mock_service.verify_customer_match.return_value = {"validMatch": True, "matchConfidence": "High"}
    return mock_service


@pytest.fixture
def mock_file_processor(mock_gemini_service, mock_qbo_service):
    """Mock file processor for tests."""
    mock_processor = Mock()
    mock_processor.gemini_service = mock_gemini_service
    mock_processor.qbo_service = mock_qbo_service
    mock_processor.process.return_value = {
        "Donor Name": "Test Donor",
        "Gift Amount": "100.00",
        "Check No.": "1234",
        "Check Date": "2024-01-01",
    }
    return mock_processor


@pytest.fixture
def mock_celery_app():
    """Mock Celery app for tests."""
    mock_app = Mock()
    mock_task = Mock()
    mock_task.id = "test-task-id"
    mock_task.state = "PENDING"
    mock_task.info = {}
    mock_app.AsyncResult.return_value = mock_task
    return mock_app


@pytest.fixture(autouse=True)
def mock_celery_tasks():
    """Mock Celery tasks to avoid import errors."""
    with patch("src.utils.tasks.process_files_task") as mock_task:
        mock_task.delay.return_value = Mock(id="test-task-id")
        yield mock_task
