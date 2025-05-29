import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from utils.gemini_service import GeminiService


class TestGeminiService(unittest.TestCase):
    def setUp(self):
        self.api_key = "test_api_key"

        # Create a mock for the Gemini service
        self.gemini_service_patcher = patch("utils.gemini_service.genai")
        self.mock_genai = self.gemini_service_patcher.start()

        # Setup the mock GenerativeModel
        self.mock_model = MagicMock()
        self.mock_genai.GenerativeModel.return_value = self.mock_model

        # Mock PromptManager
        self.prompt_manager_patcher = patch("utils.gemini_service.PromptManager")
        self.mock_prompt_manager_class = self.prompt_manager_patcher.start()
        self.mock_prompt_manager = MagicMock()
        self.mock_prompt_manager_class.return_value = self.mock_prompt_manager

        # Configure the mock prompt manager to return test prompts
        self.mock_prompt_manager.get_prompt.return_value = "Test prompt content"
        self.mock_prompt_manager.combine_prompts.return_value = "Combined test prompt"

        # Initialize the service
        self.service = GeminiService(self.api_key)

        # Create a temp directory for test files
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        self.gemini_service_patcher.stop()
        self.prompt_manager_patcher.stop()

        # Remove temp directory
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("builtins.open")
    def test_extract_donation_data_success(self, mock_open):
        """Test successful extraction of donation data."""
        # Create a test image file path
        test_image_path = os.path.join(self.temp_dir, "test_image.jpg")

        # Mock file operations
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "test prompt"
        mock_open.side_effect = [mock_file, mock_file]

        # Mock Image.open
        with patch("utils.gemini_service.Image.open") as mock_image_open:
            mock_image = MagicMock()
            mock_image_open.return_value = mock_image

            # Mock response from Gemini
            mock_response = MagicMock()
            mock_response.text = """
            {
                "customerLookup": "Smith, John",
                "Donor Name": "John Smith",
                "Gift Amount": "100.00",
                "Check No.": "1234",
                "Gift Date": "01/01/2025"
            }
            """
            self.mock_model.generate_content.return_value = mock_response

            # Test the method
            result = self.service.extract_donation_data(test_image_path)

            # Verify the result - we expect a list with one item
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            donation = result[0]
            self.assertEqual(donation["customerLookup"], "Smith, John")
            self.assertEqual(donation["Donor Name"], "John Smith")
            self.assertEqual(donation["Gift Amount"], "100.00")

            # Verify that Gemini API was called correctly
            self.mock_model.generate_content.assert_called_once()

    @patch("os.path.splitext")
    @patch("PyPDF2.PdfReader")
    @patch("fitz.open")
    @patch("utils.gemini_service.Image.open")
    def test_extract_donation_data_pdf(self, mock_image_open, mock_fitz_open, mock_pdf_reader, mock_splitext):
        """Test extraction from a PDF file."""
        # Mock file extension check
        mock_splitext.return_value = ["test", ".pdf"]

        # Setup test data
        expected_data = [
            {
                "customerLookup": "Smith, John",
                "Donor Name": "John Smith",
                "Gift Amount": "100.00",
                "Check No.": "1234",
                "Gift Date": "01/01/2025",
            }
        ]

        # Mock the extract_json_from_text method to return our test data
        with patch.object(self.service, "_extract_json_from_text", return_value=expected_data):
            # Mock response from Gemini for PDF
            mock_response = MagicMock()
            mock_response.text = """
            [
                {
                    "customerLookup": "Smith, John",
                    "Donor Name": "John Smith",
                    "Gift Amount": "100.00",
                    "Check No.": "1234",
                    "Gift Date": "01/01/2025"
                }
            ]
            """
            self.mock_model.generate_content.return_value = mock_response

            # Mock PyPDF2 reader
            mock_reader_instance = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Test PDF content"
            mock_reader_instance.pages = [mock_page]
            mock_pdf_reader.return_value = mock_reader_instance

            # Mock fitz document
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 1

            mock_page = MagicMock()
            mock_pixmap = MagicMock()
            mock_pixmap.tobytes.return_value = b"test image data"

            mock_page.get_pixmap.return_value = mock_pixmap
            mock_doc.__getitem__.return_value = mock_page
            mock_fitz_open.return_value = mock_doc

            # Mock PIL Image
            mock_image = MagicMock()
            mock_image_open.return_value = mock_image

            # Call the method being tested
            result = self.service.extract_donation_data("test.pdf")

            # Verify the result
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["customerLookup"], "Smith, John")
            self.assertEqual(result[0]["Gift Amount"], "100.00")

    def test_extract_text_data(self):
        """Test extraction of structured data from text."""
        # Mock Gemini response
        mock_response = MagicMock()
        mock_response.text = """
        [
            {
                "customerLookup": "Smith, John",
                "Donor Name": "John Smith",
                "Gift Amount": "100.00",
                "Gift Date": "01/01/2025"
            },
            {
                "customerLookup": "Doe, Jane",
                "Donor Name": "Jane Doe",
                "Gift Amount": "50.00",
                "Gift Date": "01/02/2025"
            }
        ]
        """
        self.mock_model.generate_content.return_value = mock_response

        # Test the method
        result = self.service.extract_text_data("Test prompt with CSV data")

        # Verify the results
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["Donor Name"], "John Smith")
        self.assertEqual(result[1]["Donor Name"], "Jane Doe")

    def test_extract_json_from_text(self):
        """Test extracting JSON from various text formats."""
        # Direct JSON
        json_text = '{"name": "John", "amount": "100.00"}'
        result = self.service._extract_json_from_text(json_text)
        self.assertEqual(result["name"], "John")

        # JSON inside text
        text_with_json = """
        Here is the extracted data:
        
        {"name": "John", "amount": "100.00"}
        
        Let me know if you need anything else.
        """
        result = self.service._extract_json_from_text(text_with_json)
        self.assertEqual(result["name"], "John")

        # JSON array
        array_text = """
        [
            {"name": "John", "amount": "100.00"},
            {"name": "Jane", "amount": "50.00"}
        ]
        """
        result = self.service._extract_json_from_text(array_text)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "John")

        # Malformed text (should return None)
        malformed_text = "This is not JSON"
        result = self.service._extract_json_from_text(malformed_text)
        self.assertIsNone(result)

    @patch("builtins.open")
    def test_extract_donation_data_error(self, mock_open):
        """Test handling of errors during extraction."""
        # Create a test image file path
        test_image_path = os.path.join(self.temp_dir, "test_error.jpg")

        # Mock file operations
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = "test prompt"
        mock_open.side_effect = [mock_file, mock_file]

        # Mock Image.open to raise an exception for PIL error testing
        with patch("utils.gemini_service.Image.open") as mock_image_open:
            mock_image_open.side_effect = Exception("Image error")

            # Mock API error
            self.mock_model.generate_content.side_effect = Exception("API error")

            # Test the method
            result = self.service.extract_donation_data(test_image_path)

            # Verify the result
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
