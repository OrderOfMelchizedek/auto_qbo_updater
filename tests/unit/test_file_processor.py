import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, call, patch

from PIL import Image

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from utils.file_processor import FileProcessor
from utils.prompt_manager import PromptManager


class TestFileProcessor(unittest.TestCase):
    def setUp(self):
        # Mock GeminiService
        self.gemini_service = MagicMock()

        # Mock PromptManager
        self.prompt_manager_patcher = patch("src.utils.file_processor.PromptManager")
        self.mock_prompt_manager_class = self.prompt_manager_patcher.start()
        self.mock_prompt_manager = MagicMock()
        self.mock_prompt_manager_class.return_value = self.mock_prompt_manager

        # Configure mock prompt manager
        self.mock_prompt_manager.get_prompt.return_value = "Test prompt content"
        self.mock_prompt_manager.combine_prompts.return_value = "Combined test prompt"

        # Create the FileProcessor with the mock GeminiService
        self.file_processor = FileProcessor(self.gemini_service)

        # Create a temp directory for test files
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Stop the patcher
        self.prompt_manager_patcher.stop()

        # Clean up the temporary directory
        import shutil

        shutil.rmtree(self.temp_dir)

    def disabled_test_process_image(self):
        """Test processing an image file."""
        # Create a test image file
        test_image_path = os.path.join(self.temp_dir, "test_image.jpg")
        with open(test_image_path, "wb") as f:
            f.write(b"test image data")

        # Configure the mock GeminiService to return complete data with all required fields
        test_data = {
            "customerLookup": "Smith, John",
            "Donor Name": "John Smith",
            "Gift Amount": "100.00",
            "Check No.": "1234",
            "Gift Date": "01/01/2025",
            "Address - Line 1": "123 Main St",
            "City": "Springfield",
            "State": "IL",
            "ZIP": "62701",
            "Last Name": "Smith",
        }
        self.gemini_service.extract_donation_data.return_value = [test_data]

        # Test the method
        result = self.file_processor.process(test_image_path, ".jpg")

        # Verify the result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Donor Name"], "John Smith")
        self.assertEqual(result[0]["Gift Amount"], "100.00")

        # Verify GeminiService was called correctly - it's called only once since we have all required fields
        self.gemini_service.extract_donation_data.assert_called_once_with(test_image_path)

    def disabled_test_process_pdf(self):
        """Test processing a PDF file."""
        # Create a test PDF file
        test_pdf_path = os.path.join(self.temp_dir, "test.pdf")
        with open(test_pdf_path, "wb") as f:
            f.write(b"%PDF-1.4\n")  # Minimal PDF header

        # Configure the mock GeminiService to return complete test data
        test_data = [
            {
                "customerLookup": "Smith, John",
                "Donor Name": "John Smith",
                "Gift Amount": "100.00",
                "Check No.": "1234",
                "Gift Date": "01/01/2025",
                "Address - Line 1": "123 Main St",
                "City": "Springfield",
                "State": "IL",
                "ZIP": "62701",
                "Last Name": "Smith",
            }
        ]
        self.gemini_service.extract_donation_data.return_value = test_data

        # Reset the call history
        self.gemini_service.reset_mock()

        # Test the method
        result = self.file_processor.process(test_pdf_path, ".pdf")

        # Verify the result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Donor Name"], "John Smith")

        # Verify GeminiService was called correctly
        self.gemini_service.extract_donation_data.assert_called_once_with(test_pdf_path)

    def disabled_test_process_csv(self):
        """Test processing a CSV file."""
        # Create a test CSV file
        test_csv_path = os.path.join(self.temp_dir, "test.csv")
        with open(test_csv_path, "w", encoding="utf-8") as f:
            f.write("donor_name,gift_amount,gift_date\n")
            f.write("John Doe,100.00,01/01/2025\n")

        # Configure the mock GeminiService to return test data for CSV
        test_data = [
            {
                "customerLookup": "Doe, John",
                "Donor Name": "John Doe",
                "Gift Amount": "100.00",
                "Gift Date": "01/01/2025",
            }
        ]
        self.gemini_service.extract_text_data.return_value = test_data

        # Reset and reconfigure the mock PromptManager for this test
        self.mock_prompt_manager.reset_mock()
        self.mock_prompt_manager.get_prompt.return_value = "Test CSV prompt"

        # Test the method
        result = self.file_processor.process(test_csv_path, ".csv")

        # Verify the result
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Donor Name"], "John Doe")

        # Verify the prompt manager was used correctly
        self.mock_prompt_manager.get_prompt.assert_called_with(
            "csv_extraction_prompt",
            {"csv_content": "donor_name,gift_amount,gift_date\nJohn Doe,100.00,01/01/2025\n"},
        )

    def disabled_test_process_with_validation_missing_fields(self):
        """Test processing with validation when fields are missing."""
        # Reset everything for this test
        self.gemini_service.reset_mock()
        self.mock_prompt_manager.reset_mock()

        # Create a test image file
        test_image_path = os.path.join(self.temp_dir, "test_validation.jpg")
        with open(test_image_path, "wb") as f:
            f.write(b"test image data")

        # Configure mock to return data with missing fields
        initial_data = {
            "Donor Name": "John Smith",
            "Gift Amount": "100.00",
            "Gift Date": "01/01/2025",
            # Missing Address, City, State, ZIP, Last Name
        }

        # Mock reprocessed data with the missing fields
        reprocessed_data = {
            "Donor Name": "John Smith",
            "Gift Amount": "100.00",
            "Gift Date": "01/01/2025",
            "Address - Line 1": "123 Main St",
            "City": "Springfield",
            "State": "IL",
            "ZIP": "62701",
            "Last Name": "Smith",
        }

        # Mock the behavior of the various methods
        self.mock_prompt_manager.get_prompt.return_value = "Test reprocessing prompt"

        # Monitor the get_prompt calls
        get_prompt_calls = []

        def side_effect(*args, **kwargs):
            get_prompt_calls.append((args, kwargs))
            return "Test reprocessing prompt"

        self.mock_prompt_manager.get_prompt.side_effect = side_effect

        # Configure the gemini service to return different results on each call
        self.gemini_service.extract_donation_data.side_effect = [
            [initial_data],
            [reprocessed_data],
        ]

        # Process the image
        result = self.file_processor.process(test_image_path, ".jpg")

        # Verify the reprocessing worked
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

        # Check that the missing fields were added
        self.assertEqual(result[0]["Address - Line 1"], "123 Main St")
        self.assertEqual(result[0]["City"], "Springfield")
        self.assertEqual(result[0]["State"], "IL")
        self.assertEqual(result[0]["ZIP"], "62701")
        self.assertEqual(result[0]["Last Name"], "Smith")

        # Verify extract_donation_data was called twice
        self.assertEqual(self.gemini_service.extract_donation_data.call_count, 2)

        # Verify the second call had the custom_prompt parameter
        second_call = self.gemini_service.extract_donation_data.call_args_list[1]
        self.assertEqual(second_call[0][0], test_image_path)
        self.assertEqual(second_call[1]["custom_prompt"], "Test reprocessing prompt")

        # Verify get_prompt was called with the reprocess_prompt
        self.assertEqual(self.mock_prompt_manager.get_prompt.call_count, 1)
        self.assertEqual(self.mock_prompt_manager.get_prompt.call_args[0][0], "reprocess_prompt")

    def test_unsupported_file_type(self):
        """Test handling of unsupported file types."""
        # Create a test file with unsupported extension
        test_file_path = os.path.join(self.temp_dir, "test.xyz")
        with open(test_file_path, "w") as f:
            f.write("test data")

        # Test the method
        result = self.file_processor.process(test_file_path, ".xyz")

        # Verify it returns None for unsupported types
        self.assertIsNone(result)

    def test_nonexistent_file(self):
        """Test handling of nonexistent files."""
        # Nonexistent file path
        nonexistent_path = os.path.join(self.temp_dir, "does_not_exist.jpg")

        # Configure the mock to simulate file not found
        self.gemini_service.extract_donation_data.return_value = None

        # Test the method
        result = self.file_processor.process(nonexistent_path, ".jpg")

        # Verify it returns None for nonexistent files
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
