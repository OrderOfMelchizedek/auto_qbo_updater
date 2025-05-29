"""
Unit tests for files blueprint routes.
"""

import io
import json
import os
from datetime import datetime
from unittest.mock import ANY, MagicMock, Mock, patch

import pytest
from werkzeug.datastructures import FileStorage


@pytest.fixture
def mock_file():
    """Create a mock file for upload testing."""
    file_content = b"Test file content"
    file = FileStorage(stream=io.BytesIO(file_content), filename="test_donation.csv", content_type="text/csv")
    return file


@pytest.fixture
def mock_qbo_service():
    """Create a mock QBO service."""
    mock_service = Mock()
    mock_service.find_customer.return_value = {"Id": "customer-123", "DisplayName": "Test Customer"}
    return mock_service


@pytest.fixture
def mock_file_processor():
    """Create a mock file processor."""
    mock_processor = Mock()
    mock_processor.process.return_value = [
        {"Donor Name": "John Doe", "Gift Amount": "100.00", "Check No.": "1234", "Gift Date": "2024-01-15"}
    ]
    return mock_processor


class TestFilesRoutes:
    """Test file upload and processing routes."""

    def test_upload_start_success(self, client):
        """Test starting a new upload session."""
        response = client.post("/upload-start", headers={"X-CSRFToken": "test-token"})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "session_id" in data

        # Verify session was initialized
        with client.session_transaction() as sess:
            assert sess["session_id"] == data["session_id"]
            assert sess["donations"] == []
            assert sess["upload_in_progress"] is True
            assert "upload_start_time" in sess

    def test_upload_start_error(self, client):
        """Test upload start error handling."""
        with patch("uuid.uuid4", side_effect=Exception("UUID error")):
            response = client.post("/upload-start", headers={"X-CSRFToken": "test-token"})

            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data

    @patch("utils.tasks.process_files_task")
    @patch("utils.result_store.ResultStore")
    def test_upload_async_success(self, mock_store_class, mock_task, client, mock_file):
        """Test async file upload."""
        # Mock Celery task
        mock_task_instance = Mock()
        mock_task_instance.id = "task-123"
        mock_task.delay.return_value = mock_task_instance

        # Mock result store
        mock_store = Mock()
        mock_store_class.return_value = mock_store

        with patch("services.validation.log_audit_event"):
            # Upload file
            data = {"files": (mock_file, "test_donation.csv")}
            response = client.post(
                "/upload-async", data=data, content_type="multipart/form-data", headers={"X-CSRFToken": "test-token"}
            )

            assert response.status_code == 200
            result = json.loads(response.data)
            assert result["success"] is True
            assert result["task_id"] == "task-123"
            assert "session_id" in result

            # Verify task was submitted
            mock_task.delay.assert_called_once()
            call_args = mock_task.delay.call_args[1]
            assert len(call_args["file_paths"]) == 1
            assert call_args["file_paths"][0]["original_name"] == "test_donation.csv"

    def test_upload_async_no_files(self, client):
        """Test async upload with no files."""
        response = client.post(
            "/upload-async", data={}, content_type="multipart/form-data", headers={"X-CSRFToken": "test-token"}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error"] == "No files provided"

    def test_upload_async_too_many_files(self, client):
        """Test async upload with too many files."""
        # Create 11 mock files (exceeds limit of 10)
        from werkzeug.datastructures import MultiDict

        data = MultiDict()
        for i in range(21):  # More than MAX_FILES_PER_UPLOAD (20)
            file = FileStorage(stream=io.BytesIO(b"content"), filename=f"file{i}.csv")
            data.add("files", file)

        response = client.post(
            "/upload-async", data=data, content_type="multipart/form-data", headers={"X-CSRFToken": "test-token"}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Too many files" in data["error"]

    @patch("src.utils.progress_logger.log_progress")
    @patch("src.services.validation.log_audit_event")
    def test_upload_sync_success(
        self, mock_audit, mock_progress, client, app, mock_file, mock_qbo_service, mock_file_processor
    ):
        """Test synchronous file upload."""
        # Mock memory monitor directly on app
        mock_monitor = Mock()
        app.memory_monitor = mock_monitor
        
        # Set services on app
        app.qbo_service = mock_qbo_service
        app.file_processor = mock_file_processor
        
        # Mock process_single_file function
        def mock_process_single_file(file_data, qbo_authenticated):
            return {
                "success": True,
                "filename": file_data["filename"],
                "donations": [{"Donor Name": "John Doe", "Gift Amount": "100.00", "Check No.": "1234"}],
                "file_path": "/tmp/test.csv",
                "processing_time": 0.5,
            }
        
        # Mock cleanup function
        def mock_cleanup_uploaded_file(file_path):
            pass
        
        # Set functions on app
        app.process_single_file = mock_process_single_file
        app.cleanup_uploaded_file = mock_cleanup_uploaded_file

        # Set QBO authenticated
        with client.session_transaction() as sess:
            sess["qbo_authenticated"] = True

        # Upload file
        data = {"files": (mock_file, "test_donation.csv")}
        response = client.post(
            "/upload", data=data, content_type="multipart/form-data", headers={"X-CSRFToken": "test-token"}
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["success"] is True
        assert result["total_donations"] == 1
        assert len(result["processed_files"]) == 1
        assert result["processed_files"][0]["filename"] == "test_donation.csv"
        assert result["qbo_authenticated"] is True

        # Verify memory monitoring
        mock_monitor.log_memory.assert_called()
        mock_monitor.cleanup.assert_called()

    def test_upload_sync_with_deduplication(self, client, app):
        """Test upload with deduplication of donations."""
        with (
            patch("src.utils.progress_logger.log_progress"),
            patch("src.services.validation.log_audit_event"),
        ):
            # Mock memory monitor directly on app
            mock_monitor = Mock()
            app.memory_monitor = mock_monitor

            # Set up existing donations in session (already has check 1234)
            with client.session_transaction() as sess:
                sess["donations"] = [{"Check No.": "1234", "Gift Amount": "100.00", "Donor Name": "John Doe"}]

            # Mock process_single_file function that returns duplicate and new donation
            def mock_process_single_file(file_data, qbo_authenticated):
                return {
                    "success": True,
                    "filename": "test.csv",
                    "donations": [
                        {"Check No.": "1234", "Gift Amount": "100.00", "Donor Name": "John Doe"},  # Duplicate
                        {"Check No.": "5678", "Gift Amount": "200.00", "Donor Name": "Jane Smith"},  # New
                    ],
                    "file_path": "/tmp/test.csv",
                    "processing_time": 0.5,
                }
            
            # Mock cleanup function
            def mock_cleanup_uploaded_file(file_path):
                pass
            
            # Set functions on app
            app.process_single_file = mock_process_single_file
            app.cleanup_uploaded_file = mock_cleanup_uploaded_file

            # Create mock file
            file = FileStorage(stream=io.BytesIO(b"content"), filename="test.csv")

            response = client.post(
                "/upload",
                data={"files": (file, "test.csv")},
                content_type="multipart/form-data",
                headers={"X-CSRFToken": "test-token"},
            )

            assert response.status_code == 200
            result = json.loads(response.data)
            assert result["success"] is True
            assert result["donations_found"] == 2
            # Since deduplication service merges duplicates, should still be 2 unique
            assert result["unique_donations"] == 2

    def test_upload_sync_error_handling(self, client, app, mock_file):
        """Test sync upload error handling."""
        with patch("src.services.validation.log_audit_event"):
            # Mock memory monitor directly on app
            mock_monitor = Mock()
            app.memory_monitor = mock_monitor

            # Simulate processing error
            def mock_process_single_file_error(file_data, qbo_authenticated):
                raise Exception("Processing error")
            
            # Set error function on app
            app.process_single_file = mock_process_single_file_error

            response = client.post(
                "/upload", data={"files": (mock_file, "test.csv")}, content_type="multipart/form-data",
                headers={"X-CSRFToken": "test-token"}
            )

            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data

            # Verify cleanup was called
            mock_monitor.cleanup.assert_called()

    @patch("utils.celery_app.celery_app")
    @patch("utils.result_store.ResultStore")
    def test_task_status_success(self, mock_store_class, mock_celery, client):
        """Test getting task status."""
        # Mock Celery result
        mock_result = Mock()
        mock_result.state = "SUCCESS"
        mock_result.result = {"donations": [{"id": 1}, {"id": 2}], "processed_files": 2}
        mock_result.info = None  # Not used for SUCCESS state
        mock_celery.AsyncResult.return_value = mock_result

        # Mock result store
        mock_store = Mock()
        mock_store.get_task_metadata.return_value = {"session_id": "test-session", "file_count": 2}
        mock_store_class.return_value = mock_store

        with client.session_transaction() as sess:
            sess["session_id"] = "test-session"

        response = client.get("/task-status/task-123")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["task_id"] == "task-123"
        assert data["state"] == "SUCCESS"
        assert data["status"] == "Task completed successfully"
        assert "result" in data

        # Verify donations were stored in session
        with client.session_transaction() as sess:
            assert sess["donations"] == [{"id": 1}, {"id": 2}]

    def test_task_status_pending(self, client):
        """Test task status for pending task."""
        with (
            patch("utils.celery_app.celery_app") as mock_celery,
            patch("utils.result_store.ResultStore") as mock_store_class,
        ):

            mock_result = Mock()
            mock_result.state = "PENDING"
            mock_result.info = None  # Not used for PENDING state
            mock_result.result = None  # Not used for PENDING state
            mock_celery.AsyncResult.return_value = mock_result

            mock_store = Mock()
            mock_store.get_task_metadata.return_value = {}
            mock_store_class.return_value = mock_store

            response = client.get("/task-status/task-123")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["state"] == "PENDING"
            assert data["status"] == "Task is waiting to be processed"

    def test_task_status_progress(self, client):
        """Test task status with progress updates."""
        with (
            patch("utils.celery_app.celery_app") as mock_celery,
            patch("utils.result_store.ResultStore") as mock_store_class,
        ):

            mock_result = Mock()
            mock_result.state = "PROGRESS"
            mock_result.info = {"current": 5, "total": 10, "status": "Processing file 5 of 10"}
            mock_result.result = None  # Not used for PROGRESS state
            mock_celery.AsyncResult.return_value = mock_result

            mock_store = Mock()
            mock_store.get_task_metadata.return_value = {}
            mock_store_class.return_value = mock_store

            response = client.get("/task-status/task-123")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["state"] == "PROGRESS"
            assert data["current"] == 5
            assert data["total"] == 10
            assert data["status"] == "Processing file 5 of 10"

    def test_task_status_failure(self, client):
        """Test task status for failed task."""
        with (
            patch("utils.celery_app.celery_app") as mock_celery,
            patch("utils.result_store.ResultStore") as mock_store_class,
        ):

            mock_result = Mock()
            mock_result.state = "FAILURE"
            mock_result.info = Exception("Task failed")
            mock_result.result = None  # Not used for FAILURE state
            mock_celery.AsyncResult.return_value = mock_result

            mock_store = Mock()
            mock_store.get_task_metadata.return_value = {}
            mock_store_class.return_value = mock_store

            response = client.get("/task-status/task-123")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["state"] == "FAILURE"
            assert "Task failed" in data["error"]
            assert data["status"] == "Task failed"
