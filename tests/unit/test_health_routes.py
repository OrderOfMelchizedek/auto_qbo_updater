"""
Unit tests for health blueprint routes.
"""

import json
import os
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestHealthRoutes:
    """Test health check routes."""

    def test_health_check_healthy(self, client):
        """Test health check endpoint when system is healthy."""
        with (
            patch("psutil.Process") as mock_process,
            patch("psutil.virtual_memory") as mock_memory,
            patch("src.utils.celery_app.get_redis_client") as mock_redis,
        ):

            # Mock process info
            mock_proc_instance = Mock()
            mock_proc_instance.memory_info.return_value = Mock(rss=100 * 1024 * 1024)  # 100MB
            mock_proc_instance.create_time.return_value = 1234567890
            mock_proc_instance.cpu_percent.return_value = 15.5
            mock_process.return_value = mock_proc_instance

            # Mock system memory
            mock_memory.return_value = Mock(available=1024 * 1024 * 1024)  # 1GB

            # Mock Redis
            mock_redis_instance = Mock()
            mock_redis_instance.ping.return_value = True
            mock_redis_instance.info.return_value = {
                "redis_version": "6.2.6",
                "connected_clients": 5,
                "used_memory": 50 * 1024 * 1024,
                "uptime_in_seconds": 86400,
            }
            mock_redis.return_value = mock_redis_instance

            response = client.get("/health")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert data["memory"]["status"] == "healthy"
            assert data["memory"]["used_mb"] == 100.0
            assert data["dependencies"]["redis"]["status"] == "connected"

    def test_health_check_memory_warning(self, client):
        """Test health check when memory usage is high."""
        with patch("psutil.Process") as mock_process, patch("psutil.virtual_memory") as mock_memory:

            # Mock high memory usage (80%)
            mock_proc_instance = Mock()
            mock_proc_instance.memory_info.return_value = Mock(rss=410 * 1024 * 1024)  # 410MB of 512MB
            mock_proc_instance.create_time.return_value = 1234567890
            mock_proc_instance.cpu_percent.return_value = 15.5
            mock_process.return_value = mock_proc_instance

            mock_memory.return_value = Mock(available=100 * 1024 * 1024)  # 100MB

            response = client.get("/health")

            assert response.status_code == 503  # Service unavailable
            data = json.loads(response.data)
            assert data["status"] == "warning"
            assert data["memory"]["status"] == "warning"
            assert data["memory"]["percent"] == 80.08  # 410/512 * 100

    def test_health_check_redis_error(self, client):
        """Test health check when Redis is unavailable."""
        with (
            patch("psutil.Process") as mock_process,
            patch("psutil.virtual_memory") as mock_memory,
            patch("src.utils.celery_app.get_redis_client") as mock_redis,
        ):

            # Mock process info
            mock_proc_instance = Mock()
            mock_proc_instance.memory_info.return_value = Mock(rss=100 * 1024 * 1024)
            mock_proc_instance.create_time.return_value = 1234567890
            mock_proc_instance.cpu_percent.return_value = 15.5
            mock_process.return_value = mock_proc_instance

            mock_memory.return_value = Mock(available=1024 * 1024 * 1024)

            # Mock Redis error
            mock_redis_instance = Mock()
            mock_redis_instance.ping.side_effect = Exception("Connection refused")
            mock_redis.return_value = mock_redis_instance

            response = client.get("/health")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["dependencies"]["redis"]["status"] == "error"
            assert "Connection refused" in data["dependencies"]["redis"]["error"]

    def test_readiness_check_ready(self, client, tmp_path):
        """Test readiness check when all services are ready."""
        # Create a temporary upload directory
        upload_dir = tmp_path / "uploads"
        upload_dir.mkdir()

        with patch.dict(os.environ, {"UPLOAD_FOLDER": str(upload_dir)}):
            response = client.get("/ready")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["ready"] is True
            assert data["checks"]["upload_directory"]["status"] == "ready"
            assert data["checks"]["gemini_api"]["status"] == "configured"
            assert data["checks"]["quickbooks_oauth"]["status"] == "configured"

    def test_readiness_check_missing_upload_dir(self, client):
        """Test readiness check when upload directory doesn't exist."""
        with patch.dict(os.environ, {"UPLOAD_FOLDER": "/nonexistent/directory"}):
            response = client.get("/ready")

            assert response.status_code == 503
            data = json.loads(response.data)
            assert data["ready"] is False
            assert data["checks"]["upload_directory"]["status"] == "not_found"

    def test_readiness_check_missing_credentials(self, client, monkeypatch):
        """Test readiness check when QBO credentials are missing."""
        # Remove a required QBO credential
        monkeypatch.delenv("QBO_CLIENT_SECRET", raising=False)

        response = client.get("/ready")

        assert response.status_code == 503
        data = json.loads(response.data)
        assert data["ready"] is False
        assert data["checks"]["quickbooks_oauth"]["status"] == "missing_credentials"
        assert "QBO_CLIENT_SECRET" in data["checks"]["quickbooks_oauth"]["missing"]

    def test_session_info(self, client):
        """Test session info endpoint."""
        with client.session_transaction() as sess:
            sess["session_id"] = "test-session-123"
            sess["csrf_token"] = "test-csrf-token"
            sess["qbo_authenticated"] = True
            sess["donations"] = [{"id": 1}, {"id": 2}]

        response = client.get("/session-info")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["session_id"] == "test-session-123"
        assert data["csrf_token"] == "test-csrf-token"
        assert data["qbo_authenticated"] is True
        assert data["total_donations"] == 2
        assert "session_id" in data["session_keys"]

    def test_session_info_no_session(self, client):
        """Test session info endpoint with no session."""
        response = client.get("/session-info")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["session_id"] == "No session"
        assert data["csrf_token"] == "No CSRF token"
        assert data["qbo_authenticated"] is False
        assert data["total_donations"] == 0

    def test_test_progress_endpoint(self, client):
        """Test the progress streaming test endpoint."""
        response = client.get("/test-progress")

        assert response.status_code == 200
        assert response.content_type.startswith("text/event-stream")

        # Read first event
        data = response.get_data(as_text=True)
        lines = data.strip().split("\n\n")

        # Should have at least one event
        assert len(lines) > 0

        # Parse first event
        first_event = lines[0]
        assert "data: " in first_event
        event_data = json.loads(first_event.replace("data: ", ""))
        assert "progress" in event_data
        assert "message" in event_data

    def test_health_check_exception_handling(self, client):
        """Test health check handles exceptions gracefully."""
        with patch("psutil.Process") as mock_process:
            mock_process.side_effect = Exception("Process error")

            response = client.get("/health")

            assert response.status_code == 503
            data = json.loads(response.data)
            assert data["status"] == "error"
            assert "Process error" in data["error"]

    def test_readiness_check_exception_handling(self, client):
        """Test readiness check handles exceptions gracefully."""
        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = Exception("OS error")

            response = client.get("/ready")

            assert response.status_code == 503
            data = json.loads(response.data)
            assert data["ready"] is False
            assert data.get("ready") is False  # Changed to check ready status
