import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.gemini_service import GeminiService

class TestGeminiService(unittest.TestCase):
    def setUp(self):
        self.api_key = 'test_api_key'
        
        # Create a mock for the Gemini service
        self.gemini_service_patcher = patch('utils.gemini_service.genai')
        self.mock_genai = self.gemini_service_patcher.start()
        
        # Setup the mock GenerativeModel
        self.mock_model = MagicMock()
        self.mock_genai.GenerativeModel.return_value = self.mock_model
        
        # Initialize the service
        self.service = GeminiService(self.api_key)
    
    def tearDown(self):
        self.gemini_service_patcher.stop()
    
    @patch('builtins.open')
    def test_extract_donation_data_success(self, mock_open):
        """Test successful extraction of donation data."""
        # Mock file operations
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = 'test prompt'
        mock_open.side_effect = [mock_file, mock_file]
        
        # Mock response from Gemini
        mock_response = MagicMock()
        mock_candidate = MagicMock()
        mock_part = MagicMock()
        
        # Set up function call response
        mock_part.function_call.name = 'extract_donation'
        mock_part.function_call.args = json.dumps({
            'customerLookup': 'Smith, John',
            'Donor Name': 'John Smith',
            'Gift Amount': '100.00',
            'Check No.': '1234',
            'Gift Date': '01/01/2025'
        })
        
        mock_candidate.content.parts = [mock_part]
        mock_response.candidates = [mock_candidate]
        self.mock_model.generate_content.return_value = mock_response
        
        # Test the method
        result = self.service.extract_donation_data('test_image.jpg')
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result['customerLookup'], 'Smith, John')
        self.assertEqual(result['Donor Name'], 'John Smith')
        self.assertEqual(result['Gift Amount'], '100.00')
        
        # Verify that Gemini API was called correctly
        self.mock_model.generate_content.assert_called_once()
    
    @patch('builtins.open')
    def test_extract_donation_data_text_response(self, mock_open):
        """Test extraction from text response when function call not used."""
        # Mock file operations
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = 'test prompt'
        mock_open.side_effect = [mock_file, mock_file]
        
        # Mock text response from Gemini
        mock_response = MagicMock()
        mock_response.text = '''
        Here's the extracted data:
        
        ```json
        {
            "customerLookup": "Smith, John",
            "Donor Name": "John Smith",
            "Gift Amount": "100.00",
            "Check No.": "1234",
            "Gift Date": "01/01/2025"
        }
        ```
        '''
        
        # No function call in this case
        mock_response.candidates = []
        self.mock_model.generate_content.return_value = mock_response
        
        # Test the method
        result = self.service.extract_donation_data('test_image.jpg')
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result['customerLookup'], 'Smith, John')
        self.assertEqual(result['Donor Name'], 'John Smith')
        self.assertEqual(result['Gift Amount'], '100.00')
    
    @patch('builtins.open')
    def test_extract_donation_data_error(self, mock_open):
        """Test handling of errors during extraction."""
        # Mock file operations
        mock_file = MagicMock()
        mock_file.__enter__.return_value.read.return_value = 'test prompt'
        mock_open.side_effect = [mock_file, mock_file]
        
        # Mock API error
        self.mock_model.generate_content.side_effect = Exception('API error')
        
        # Test the method
        result = self.service.extract_donation_data('test_image.jpg')
        
        # Verify the result
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()