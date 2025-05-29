"""Integration tests for batch processing and resource management."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from utils.batch_processor import BatchProcessor, ProcessingBatch
from utils.gemini_service import GeminiService
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

    def test_batch_processor_with_progress_logging(self):
        """Test batch processor integration with progress logging."""
        # Create Gemini service
        gemini_service = GeminiService(api_key="test-key")

        # Create progress logger
        progress_logger = ProgressLogger()

        # Create batch processor
        batch_processor = BatchProcessor(
            gemini_service=gemini_service, progress_logger=progress_logger
        )

        # Create test image files instead of PDFs for simpler testing
        image_path = os.path.join(self.temp_dir, "test.jpg")
        img = Image.new("RGB", (1, 1), color="white")
        img.save(image_path, "JPEG")

        # Test batch preparation
        batches = batch_processor.prepare_batches([(image_path, ".jpg")])

        # Verify batches created
        self.assertIsInstance(batches, list)
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0].batch_type, "image")

    def test_concurrent_batch_processing(self):
        """Test concurrent processing of multiple batches."""
        # Create Gemini service
        gemini_service = GeminiService(api_key="test-key")

        # Create batch processor
        batch_processor = BatchProcessor(gemini_service=gemini_service, progress_logger=None)

        # Create multiple real image files
        image_paths = []
        for i in range(3):
            image_path = os.path.join(self.temp_dir, f"image_{i}.jpg")
            img = Image.new("RGB", (1, 1), color="white")
            img.save(image_path, "JPEG")
            image_paths.append(image_path)

        # Mock the extract_donation_data method
        with patch.object(GeminiService, "extract_donation_data") as mock_extract:
            mock_extract.return_value = {
                "Donor Name": "Test Donor",
                "Gift Amount": "100.00",
                "Check No.": "123",
            }

            # Process images concurrently
            batches = [
                ProcessingBatch(
                    batch_id=f"image_{i}",
                    batch_type="image",
                    file_path=path,
                    page_numbers=[],
                    content=None,
                    metadata={},
                )
                for i, path in enumerate(image_paths)
            ]

            donations, errors = batch_processor.process_batches_concurrently(batches)

            # Verify results
            self.assertEqual(len(donations), 3)
            self.assertEqual(len(errors), 0)
            for donation in donations:
                self.assertEqual(donation["Donor Name"], "Test Donor")
                self.assertEqual(donation["Gift Amount"], "100.00")

    def test_batch_processing_error_handling(self):
        """Test error handling in batch processing."""
        # Create batch processor
        gemini_service = GeminiService(api_key="test-key")
        batch_processor = BatchProcessor(gemini_service=gemini_service, progress_logger=None)

        # Create a test image file for the batch
        image_path = os.path.join(self.temp_dir, "test.jpg")
        img = Image.new("RGB", (1, 1), color="white")
        img.save(image_path, "JPEG")

        # Create a test batch
        batch = ProcessingBatch(
            batch_id="test_batch",
            batch_type="image",
            file_path=image_path,
            page_numbers=[],
            content=None,
            metadata={},
        )

        # Mock the GeminiService method to raise an exception
        with patch.object(
            GeminiService, "extract_donation_data", side_effect=Exception("Processing failed")
        ):
            donations, errors = batch_processor.process_batches_concurrently([batch])

        # Verify error was captured
        self.assertEqual(len(donations), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("Error in batch", errors[0])


if __name__ == "__main__":
    unittest.main()
