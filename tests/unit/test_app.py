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
    

if __name__ == '__main__':
    unittest.main()