"""Integration tests for end-to-end file processing."""

import io
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from utils.file_processor import FileProcessor
from utils.gemini_service import GeminiService


class TestFileProcessingIntegration(unittest.TestCase):
    """Test the integration between FileProcessor and GeminiService."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

        # Mock environment variables
        self.env_patcher = patch.dict(
            os.environ,
            {
                "GEMINI_API_KEY": "test-key",
                "PROMPT_DIR": os.path.join(os.path.dirname(__file__), "../../docs/prompts_archive"),
            },
        )
        self.env_patcher.start()

    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_csv_to_donations_flow(self):
        """Test complete flow from CSV file to donation data."""
        # Create a test CSV file
        csv_content = """Donor Name,Gift Amount,Gift Date,Check No.
John Smith,100.00,2024-01-15,1234
Jane Doe,250.50,2024-01-16,1235
"""
        csv_path = os.path.join(self.temp_dir, "test_donations.csv")
        with open(csv_path, "w") as f:
            f.write(csv_content)

        # Mock the extract_text_data method directly
        with patch.object(GeminiService, "extract_text_data") as mock_extract:
            mock_extract.return_value = [
                {
                    "Donor Name": "John Smith",
                    "Gift Amount": "100.00",
                    "Gift Date": "2024-01-15",
                    "Check No.": "1234",
                    "customerLookup": "Smith, John",
                },
                {
                    "Donor Name": "Jane Doe",
                    "Gift Amount": "250.50",
                    "Gift Date": "2024-01-16",
                    "Check No.": "1235",
                    "customerLookup": "Doe, Jane",
                },
            ]

            # Create services and process file
            gemini_service = GeminiService(api_key="test-key")
            file_processor = FileProcessor(gemini_service)

            # Process the CSV
            result = file_processor.process(csv_path, ".csv")

            # Verify results
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["Donor Name"], "John Smith")
            self.assertEqual(result[0]["Gift Amount"], "100.00")
            self.assertEqual(result[1]["Donor Name"], "Jane Doe")
            self.assertEqual(result[1]["Gift Amount"], "250.50")

    def test_image_to_donations_flow(self):
        """Test complete flow from image file to donation data."""
        # Create a real test image file (1x1 pixel PNG)
        image_path = os.path.join(self.temp_dir, "test_donation.jpg")

        # Create a minimal 1x1 pixel image
        img = Image.new("RGB", (1, 1), color="white")
        img.save(image_path, "JPEG")

        # Mock the extract_donation_data method directly
        with patch.object(GeminiService, "extract_donation_data") as mock_extract:
            mock_extract.return_value = {
                "Donor Name": "Test Donor",
                "Gift Amount": "500.00",
                "Gift Date": "2024-01-20",
                "Check No.": "5678",
                "customerLookup": "Donor, Test",
            }

            # Create services and process file
            gemini_service = GeminiService(api_key="test-key")
            file_processor = FileProcessor(gemini_service)

            # Process the image
            result = file_processor.process(image_path, ".jpg")

            # Verify results
            self.assertIsNotNone(result)
            self.assertEqual(result["Donor Name"], "Test Donor")
            self.assertEqual(result["Gift Amount"], "500.00")

    def test_batch_processing_multiple_files(self):
        """Test processing multiple files in sequence."""
        # Create multiple test files
        files = []
        for i in range(3):
            csv_content = f"Donor Name,Gift Amount,Gift Date,Check No.\nDonor {i},100.00,2024-01-{i+1:02d},{i+1000}\n"
            csv_path = os.path.join(self.temp_dir, f"test_{i}.csv")
            with open(csv_path, "w") as f:
                f.write(csv_content)
            files.append(csv_path)

        # Mock the extract_text_data method to return different results
        def mock_extract_side_effect(prompt_text):
            # Extract the file index from the CSV content in the prompt
            for i in range(3):
                if f"Donor {i}" in prompt_text:
                    return [
                        {
                            "Donor Name": f"Donor {i}",
                            "Gift Amount": "100.00",
                            "Gift Date": f"2024-01-{i+1:02d}",
                            "Check No.": str(i + 1000),
                            "customerLookup": f"{i}, Donor",
                        }
                    ]
            return []

        with patch.object(GeminiService, "extract_text_data", side_effect=mock_extract_side_effect):
            # Create services
            gemini_service = GeminiService(api_key="test-key")
            file_processor = FileProcessor(gemini_service)

            # Process all files
            all_results = []
            for file_path in files:
                result = file_processor.process(file_path, ".csv")
                if result:
                    all_results.extend(result)

            # Verify results
            self.assertEqual(len(all_results), 3)
            for i, donation in enumerate(all_results):
                self.assertEqual(donation["Donor Name"], f"Donor {i}")
                self.assertEqual(donation["Check No."], str(i + 1000))


if __name__ == "__main__":
    unittest.main()
