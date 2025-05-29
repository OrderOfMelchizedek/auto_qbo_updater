"""Integration tests for memory management and monitoring."""

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from utils.memory_monitor import MemoryMonitor
from utils.temp_file_manager import TempFileManager


class TestMemoryIntegration(unittest.TestCase):
    """Test memory management across components."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.memory_monitor = MemoryMonitor()
        self.temp_manager = TempFileManager()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_temp_file_cleanup_reduces_memory(self):
        """Test that cleaning temp files reduces memory usage."""
        # Create some large temporary files
        temp_files = []
        for i in range(5):
            temp_file = os.path.join(self.temp_dir, f"large_file_{i}.dat")
            with open(temp_file, "wb") as f:
                # Write 10MB of data
                f.write(b"x" * (10 * 1024 * 1024))
            temp_files.append(temp_file)
            self.temp_manager.register_file(temp_file)

        # Check initial file count
        self.assertEqual(len(self.temp_manager._temp_files), 5)

        # Clean up old files (with mocked age check)
        with patch("os.path.getmtime") as mock_getmtime:
            # Make files appear old
            mock_getmtime.return_value = time.time() - 3700  # Over 1 hour old
            cleaned = self.temp_manager.cleanup_old_files(max_age_hours=1)

        # Verify files were cleaned
        self.assertEqual(cleaned, 5)
        for temp_file in temp_files:
            self.assertFalse(os.path.exists(temp_file))

    @patch("psutil.Process")
    def test_memory_monitoring_with_threshold(self, mock_process):
        """Test memory monitoring with threshold alerts."""
        # Mock memory usage
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 500 * 1024 * 1024  # 500 MB
        mock_process.return_value.memory_info.return_value = mock_memory_info

        # Check if memory exceeds threshold
        memory_mb = self.memory_monitor.get_memory_usage()
        self.assertAlmostEqual(memory_mb, 500.0, places=1)

        # Test threshold check
        exceeds = self.memory_monitor.check_memory_threshold(threshold_mb=400)
        self.assertTrue(exceeds)

        exceeds = self.memory_monitor.check_memory_threshold(threshold_mb=600)
        self.assertFalse(exceeds)

    def test_file_processing_with_memory_limits(self):
        """Test file processing respects memory limits."""
        from utils.batch_processor import BatchProcessor

        # Create a batch processor with memory monitoring
        with patch("utils.gemini_service.GeminiService") as mock_gemini:
            mock_gemini_instance = MagicMock()
            mock_gemini.return_value = mock_gemini_instance

            batch_processor = BatchProcessor(gemini_service=mock_gemini_instance, progress_logger=None)

            # Create test PDF file
            pdf_path = os.path.join(self.temp_dir, "test.pdf")
            with open(pdf_path, "wb") as f:
                f.write(b"%PDF-1.4\n%fake pdf content")

            # Process with batch size limits
            batches = batch_processor._split_pdf_into_batches(
                pdf_path, total_pages=100, max_pages_per_batch=10  # Simulate 100 page PDF
            )

            # Verify batching respects limits
            self.assertEqual(len(batches), 10)  # 100 pages / 10 per batch
            for batch in batches:
                self.assertLessEqual(len(batch.page_numbers), 10)

    def test_redis_memory_usage_tracking(self):
        """Test Redis memory usage tracking."""
        with patch("redis.StrictRedis") as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client

            # Mock Redis info
            mock_client.info.return_value = {
                "used_memory": 50 * 1024 * 1024,  # 50 MB
                "used_memory_peak": 100 * 1024 * 1024,  # 100 MB peak
                "connected_clients": 5,
            }

            from utils.redis_monitor import get_redis_memory_info

            info = get_redis_memory_info(mock_client)
            self.assertEqual(info["used_memory_mb"], 50.0)
            self.assertEqual(info["peak_memory_mb"], 100.0)
            self.assertEqual(info["connected_clients"], 5)


if __name__ == "__main__":
    unittest.main()
