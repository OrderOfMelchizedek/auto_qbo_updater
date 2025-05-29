"""Integration tests for batch processing and resource management."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from utils.batch_processor import BatchProcessor
from utils.progress_logger import ProgressLogger


class TestBatchProcessingIntegration(unittest.TestCase):
    """Test batch processing integration."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("utils.gemini_service.GeminiService")
    def test_batch_processor_with_progress_logging(self, mock_gemini):
        """Test batch processor integration with progress logging."""
        # Mock Gemini service
        mock_gemini_instance = MagicMock()
        mock_gemini.return_value = mock_gemini_instance

        # Create progress logger
        progress_logger = ProgressLogger()

        # Create batch processor
        batch_processor = BatchProcessor(gemini_service=mock_gemini_instance, progress_logger=progress_logger)

        # Create test PDF path
        pdf_path = os.path.join(self.temp_dir, "test.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\n%fake pdf content")

        # Test batch splitting
        batches = batch_processor._split_pdf_into_batches(pdf_path, total_pages=50, max_pages_per_batch=10)

        # Verify batches created correctly
        self.assertEqual(len(batches), 5)
        for i, batch in enumerate(batches):
            self.assertEqual(batch.batch_type, "pdf")
            self.assertEqual(batch.file_path, pdf_path)
            self.assertEqual(len(batch.page_numbers), 10)

    @patch("utils.gemini_service.GeminiService")
    def test_concurrent_batch_processing(self, mock_gemini):
        """Test concurrent processing of multiple batches."""
        # Mock Gemini service
        mock_gemini_instance = MagicMock()
        mock_gemini_instance.extract_donation_data.return_value = [
            {"Donor Name": "Test Donor", "Gift Amount": "100.00"}
        ]

        # Create batch processor
        batch_processor = BatchProcessor(gemini_service=mock_gemini_instance, progress_logger=None)

        # Create multiple image files
        image_paths = []
        for i in range(3):
            image_path = os.path.join(self.temp_dir, f"image_{i}.jpg")
            with open(image_path, "wb") as f:
                f.write(b"fake image data")
            image_paths.append(image_path)

        # Process images concurrently
        from utils.batch_processor import ProcessingBatch

        batches = [
            ProcessingBatch(
                batch_id=f"image_{i}", batch_type="image", file_path=path, page_numbers=[], content=None, metadata={}
            )
            for i, path in enumerate(image_paths)
        ]

        donations, errors = batch_processor.process_batches_concurrently(batches)

        # Verify results
        self.assertEqual(len(donations), 3)
        self.assertEqual(len(errors), 0)
        self.assertEqual(mock_gemini_instance.extract_donation_data.call_count, 3)

    @patch("utils.batch_processor.ThreadPoolExecutor")
    def test_batch_processing_error_handling(self, mock_executor):
        """Test error handling in batch processing."""
        # Mock executor to simulate an error
        mock_future = MagicMock()
        mock_future.result.side_effect = Exception("Processing failed")

        mock_executor_instance = MagicMock()
        mock_executor_instance.__enter__ = MagicMock(return_value=mock_executor_instance)
        mock_executor_instance.__exit__ = MagicMock(return_value=None)
        mock_executor_instance.submit.return_value = mock_future
        mock_executor.return_value = mock_executor_instance

        # Create batch processor
        with patch("utils.gemini_service.GeminiService") as mock_gemini:
            batch_processor = BatchProcessor(gemini_service=mock_gemini.return_value, progress_logger=None)

            # Create a test batch
            from utils.batch_processor import ProcessingBatch

            batch = ProcessingBatch(
                batch_id="test_batch",
                batch_type="image",
                file_path="/tmp/test.jpg",
                page_numbers=[],
                content=None,
                metadata={},
            )

            # Mock as_completed to return our future
            with patch("utils.batch_processor.as_completed", return_value=[mock_future]):
                donations, errors = batch_processor.process_batches_concurrently([batch])

            # Verify error was captured
            self.assertEqual(len(donations), 0)
            self.assertEqual(len(errors), 1)
            self.assertIn("Error processing batch", errors[0])


if __name__ == "__main__":
    unittest.main()
