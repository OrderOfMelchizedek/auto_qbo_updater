import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import app

class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Set up test environment
        self.app.config['UPLOAD_FOLDER'] = 'test_uploads'
        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    def tearDown(self):
        # Clean up test uploads
        import shutil
        if os.path.exists(self.app.config['UPLOAD_FOLDER']):
            shutil.rmtree(self.app.config['UPLOAD_FOLDER'])
    
    def test_index_route(self):
        """Test that the index route returns the main page."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'FoM Donation Processor', response.data)
    
    @patch('app.csv_parser.parse')
    def test_upload_csv(self, mock_parse):
        """Test uploading a CSV file."""
        # Mock the CSV parser to return sample data
        mock_parse.return_value = [
            {
                'Donor Name': 'Test Donor',
                'Gift Amount': '100.00',
                'Gift Date': '01/01/2025'
            }
        ]
        
        # Create a test CSV file
        test_csv = 'test.csv'
        with open(os.path.join(self.app.config['UPLOAD_FOLDER'], test_csv), 'w') as f:
            f.write('Donor Name,Gift Amount,Gift Date\nTest Donor,100.00,01/01/2025')
        
        # Upload the CSV file
        with open(os.path.join(self.app.config['UPLOAD_FOLDER'], test_csv), 'rb') as f:
            response = self.client.post(
                '/upload',
                data={
                    'files': (f, test_csv)
                },
                content_type='multipart/form-data'
            )
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['donations']), 1)
        self.assertEqual(data['donations'][0]['Donor Name'], 'Test Donor')
        self.assertEqual(data['donations'][0]['dataSource'], 'CSV')
    
    @patch('app.gemini_service.extract_donation_data')
    def test_upload_image(self, mock_extract):
        """Test uploading an image file."""
        # Mock the Gemini service to return sample data
        mock_extract.return_value = {
            'customerLookup': 'Smith, John',
            'Donor Name': 'John Smith',
            'Gift Amount': '200.00',
            'Check No.': '1234',
            'Gift Date': '01/01/2025'
        }
        
        # Create a test image file (just a text file for testing)
        test_image = 'test.jpg'
        with open(os.path.join(self.app.config['UPLOAD_FOLDER'], test_image), 'w') as f:
            f.write('This is a test image file')
        
        # Upload the image file
        with open(os.path.join(self.app.config['UPLOAD_FOLDER'], test_image), 'rb') as f:
            response = self.client.post(
                '/upload',
                data={
                    'files': (f, test_image)
                },
                content_type='multipart/form-data'
            )
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['donations']), 1)
        self.assertEqual(data['donations'][0]['Donor Name'], 'John Smith')
        self.assertEqual(data['donations'][0]['dataSource'], 'LLM')

if __name__ == '__main__':
    unittest.main()