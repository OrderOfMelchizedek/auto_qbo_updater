"""Integration tests for Celery task processing."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))


class TestCeleryIntegration(unittest.TestCase):
    """Test Celery task integration with Redis."""

    def setUp(self):
        """Set up test environment."""
        # Mock Redis and Celery
        self.redis_patcher = patch("redis.StrictRedis")
        self.mock_redis = self.redis_patcher.start()

        # Mock Celery app
        self.celery_patcher = patch("utils.celery_app.celery_app")
        self.mock_celery = self.celery_patcher.start()

    def tearDown(self):
        """Clean up patches."""
        self.redis_patcher.stop()
        self.celery_patcher.stop()

    @patch("utils.file_processor.FileProcessor")
    @patch("utils.gemini_service.GeminiService")
    def test_process_file_task(self, mock_gemini, mock_processor):
        """Test the process_file Celery task."""
        from utils.tasks import process_file

        # Mock file processing
        mock_processor_instance = MagicMock()
        mock_processor_instance.process.return_value = [{"Donor Name": "Test Donor", "Gift Amount": "100.00"}]
        mock_processor.return_value = mock_processor_instance

        # Test task execution
        task_id = "test-task-123"
        file_path = "/tmp/test.csv"

        with patch("utils.tasks.progress_logger") as mock_logger:
            result = process_file(file_path, task_id)

        # Verify task completed
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["donations"]), 1)
        self.assertEqual(result["donations"][0]["Donor Name"], "Test Donor")

    @patch("utils.result_store.ResultStore")
    def test_result_store_integration(self, mock_result_store):
        """Test ResultStore integration with Redis."""
        from utils.result_store import ResultStore

        # Create a mock result store instance
        store = ResultStore()
        store.redis_client = MagicMock()

        # Test storing results
        task_id = "test-task-456"
        results = {"status": "completed", "donations": [{"Donor Name": "John Doe", "Gift Amount": "200.00"}]}

        store.store_result(task_id, results)

        # Verify Redis operations
        store.redis_client.setex.assert_called_once()
        call_args = store.redis_client.setex.call_args
        self.assertEqual(call_args[0][0], f"result:{task_id}")

    def test_redis_connection_handling(self):
        """Test Redis connection error handling."""
        from utils.celery_app import get_redis_client

        # Test connection failure
        self.mock_redis.side_effect = Exception("Connection failed")

        with self.assertRaises(Exception):
            get_redis_client()

        # Test successful connection
        self.mock_redis.side_effect = None
        mock_client = MagicMock()
        self.mock_redis.return_value = mock_client

        client = get_redis_client()
        self.assertIsNotNone(client)


if __name__ == "__main__":
    unittest.main()
