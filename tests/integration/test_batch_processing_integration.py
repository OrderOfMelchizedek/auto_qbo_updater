"""Integration tests for batch processing and resource management."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from utils.batch_processor import BatchProcessor, ProcessingBatch
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

    @patch("src.utils.gemini_service.genai")
    def test_batch_processor_with_progress_logging(self, mock_genai):
        """Test batch processor integration with progress logging."""
        # Set up mock Gemini
        mock_genai.configure = MagicMock()

        # Create Gemini service with mocked API
        from utils.gemini_service import GeminiService

        gemini_service = GeminiService(api_key="test-key")

        # Create progress logger
        progress_logger = ProgressLogger()

        # Create batch processor
        batch_processor = BatchProcessor(gemini_service=gemini_service, progress_logger=progress_logger)

        # Create test PDF path
        pdf_path = os.path.join(self.temp_dir, "test.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\n%fake pdf content")

        # Test batch preparation
        batches = batch_processor.prepare_batches([(pdf_path, ".pdf")])

        # Verify batches created (empty since our fake PDF has no pages)
        self.assertIsInstance(batches, list)

    @patch("src.utils.gemini_service.genai")
    def test_concurrent_batch_processing(self, mock_genai):
        """Test concurrent processing of multiple batches."""
        # Set up mock Gemini
        mock_genai.configure = MagicMock()
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '[{"Donor Name": "Test Donor", "Gift Amount": "100.00"}]'
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Create Gemini service
        from utils.gemini_service import GeminiService

        gemini_service = GeminiService(api_key="test-key")

        # Create batch processor
        batch_processor = BatchProcessor(gemini_service=gemini_service, progress_logger=None)

        # Create multiple image files
        image_paths = []
        for i in range(3):
            image_path = os.path.join(self.temp_dir, f"image_{i}.jpg")
            with open(image_path, "wb") as f:
                f.write(b"fake image data")
            image_paths.append(image_path)

        # Process images concurrently
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

    @patch("src.utils.batch_processor.ThreadPoolExecutor")
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
        with patch("src.utils.gemini_service.genai") as mock_genai:
            mock_genai.configure = MagicMock()

            from utils.gemini_service import GeminiService

            gemini_service = GeminiService(api_key="test-key")
            batch_processor = BatchProcessor(gemini_service=gemini_service, progress_logger=None)

            # Create a test batch
            batch = ProcessingBatch(
                batch_id="test_batch",
                batch_type="image",
                file_path="/tmp/test.jpg",
                page_numbers=[],
                content=None,
                metadata={},
            )

            # Mock as_completed to return our future
            with patch("src.utils.batch_processor.as_completed", return_value=[mock_future]):
                donations, errors = batch_processor.process_batches_concurrently([batch])

            # Verify error was captured
            self.assertEqual(len(donations), 0)
            self.assertEqual(len(errors), 1)
            self.assertIn("Error processing batch", errors[0])


if __name__ == "__main__":
    unittest.main()
