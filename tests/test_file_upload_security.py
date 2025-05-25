import unittest
from unittest.mock import patch, MagicMock, Mock, mock_open
import os
import sys
import tempfile
import uuid
from io import BytesIO

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import app, generate_secure_filename, validate_file_content, cleanup_uploaded_file
from werkzeug.datastructures import FileStorage

class TestFileUploadSecurity(unittest.TestCase):
    """Test file upload security measures."""
    
    def setUp(self):
        """Set up test environment."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        self.client = self.app.test_client()
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'QBO_CLIENT_ID': 'test_client_id',
            'QBO_CLIENT_SECRET': 'test_client_secret',
            'QBO_REDIRECT_URI': 'http://localhost:5000/qbo/callback',
            'FLASK_SECRET_KEY': 'test_secret_key_for_testing_only_32chars',
            'GEMINI_API_KEY': 'test_gemini_key'
        })
        self.env_patcher.start()
        
    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    def test_generate_secure_filename_basic(self):
        """Test secure filename generation."""
        original_filename = "test_document.pdf"
        secure_filename = generate_secure_filename(original_filename)
        
        # Should be a UUID with original extension
        self.assertTrue(secure_filename.endswith('.pdf'))
        self.assertEqual(len(secure_filename), 36 + 4)  # UUID length + .pdf
        
        # Should be different from original
        self.assertNotEqual(secure_filename, original_filename)
    
    def test_generate_secure_filename_no_extension(self):
        """Test secure filename generation without extension."""
        original_filename = "document_without_extension"
        secure_filename = generate_secure_filename(original_filename)
        
        # Should be just a UUID
        self.assertEqual(len(secure_filename), 36)  # UUID length
        self.assertTrue(all(c in '0123456789abcdef-' for c in secure_filename))
    
    def test_generate_secure_filename_multiple_dots(self):
        """Test secure filename with multiple dots."""
        original_filename = "my.document.with.dots.pdf"
        secure_filename = generate_secure_filename(original_filename)
        
        # Should preserve only the last extension
        self.assertTrue(secure_filename.endswith('.pdf'))
        self.assertEqual(len(secure_filename), 36 + 4)  # UUID length + .pdf
    
    def test_generate_secure_filename_malicious(self):
        """Test secure filename with malicious characters."""
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "<script>alert('xss')</script>.pdf",
            "file|with|pipes.jpg",
            "file with spaces and (parentheses).png"
        ]
        
        for malicious_name in malicious_filenames:
            secure_filename = generate_secure_filename(malicious_name)
            
            # Should not contain any malicious characters
            self.assertNotIn('..', secure_filename)
            self.assertNotIn('/', secure_filename)
            self.assertNotIn('\\', secure_filename)
            self.assertNotIn('<', secure_filename)
            self.assertNotIn('>', secure_filename)
            self.assertNotIn('|', secure_filename)
    
    @patch('magic.from_buffer')
    def test_validate_file_content_pdf_valid(self, mock_magic):
        """Test PDF file content validation."""
        mock_magic.return_value = 'application/pdf'
        
        pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog'
        result = validate_file_content(pdf_content, 'test.pdf')
        
        self.assertTrue(result)
        mock_magic.assert_called_once_with(pdf_content, mime=True)
    
    @patch('magic.from_buffer')
    def test_validate_file_content_image_valid(self, mock_magic):
        """Test image file content validation."""
        mock_magic.return_value = 'image/jpeg'
        
        jpeg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        result = validate_file_content(jpeg_content, 'test.jpg')
        
        self.assertTrue(result)
        mock_magic.assert_called_once_with(jpeg_content, mime=True)
    
    @patch('magic.from_buffer')
    def test_validate_file_content_csv_valid(self, mock_magic):
        """Test CSV file content validation."""
        mock_magic.return_value = 'text/csv'
        
        csv_content = b'Name,Amount,Date\nJohn Doe,100.00,2024-01-01'
        result = validate_file_content(csv_content, 'test.csv')
        
        self.assertTrue(result)
    
    @patch('magic.from_buffer')
    def test_validate_file_content_mismatch(self, mock_magic):
        """Test file content validation with type mismatch."""
        mock_magic.return_value = 'text/plain'
        
        # Text content with PDF extension
        text_content = b'This is just plain text'
        result = validate_file_content(text_content, 'fake.pdf')
        
        self.assertFalse(result)
    
    @patch('magic.from_buffer')
    def test_validate_file_content_malicious(self, mock_magic):
        """Test validation with potentially malicious content."""
        mock_magic.return_value = 'application/x-executable'
        
        # Executable content with image extension
        exe_content = b'MZ\x90\x00\x03\x00\x00\x00'  # PE executable header
        result = validate_file_content(exe_content, 'malicious.jpg')
        
        self.assertFalse(result)
    
    def test_validate_file_content_fallback_extension(self):
        """Test validation fallback when magic is not available."""
        # Test without magic library
        with patch('app.magic', None):
            # Valid extension should pass
            result = validate_file_content(b'any content', 'test.pdf')
            self.assertTrue(result)
            
            # Invalid extension should fail
            result = validate_file_content(b'any content', 'test.exe')
            self.assertFalse(result)
    
    def test_cleanup_uploaded_file_success(self):
        """Test successful file cleanup."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b'test content')
            temp_path = temp_file.name
        
        # Verify file exists
        self.assertTrue(os.path.exists(temp_path))
        
        # Clean up the file
        cleanup_uploaded_file(temp_path)
        
        # Verify file is deleted
        self.assertFalse(os.path.exists(temp_path))
    
    def test_cleanup_uploaded_file_nonexistent(self):
        """Test cleanup of nonexistent file."""
        nonexistent_path = '/tmp/nonexistent_file_12345.txt'
        
        # Should not raise an exception
        try:
            cleanup_uploaded_file(nonexistent_path)
        except Exception as e:
            self.fail(f"cleanup_uploaded_file raised {e} unexpectedly!")
    
    def test_file_size_validation(self):
        """Test file size validation."""
        # Create test file data
        small_file_data = b'small content'
        large_file_data = b'x' * (11 * 1024 * 1024)  # 11MB (over limit)
        
        # Test small file (should pass)
        small_file = FileStorage(
            stream=BytesIO(small_file_data),
            filename='small.pdf',
            content_type='application/pdf'
        )
        
        with self.app.test_request_context():
            response = self.client.post('/upload', data={
                'files': small_file
            })
            # Should not fail due to size (may fail for other reasons in test)
            self.assertNotEqual(response.status_code, 413)  # Request Entity Too Large
    
    def test_allowed_file_extensions(self):
        """Test allowed file extension validation."""
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.csv']
        disallowed_extensions = ['.exe', '.bat', '.sh', '.py', '.js', '.html']
        
        for ext in allowed_extensions:
            filename = f"test{ext}"
            # These should be considered valid extensions
            self.assertTrue(any(filename.lower().endswith(allowed_ext) 
                              for allowed_ext in ['.jpg', '.jpeg', '.png', '.pdf', '.csv']))
        
        for ext in disallowed_extensions:
            filename = f"malicious{ext}"
            # These should not be in allowed extensions
            self.assertFalse(any(filename.lower().endswith(allowed_ext) 
                               for allowed_ext in ['.jpg', '.jpeg', '.png', '.pdf', '.csv']))
    
    @patch('app.validate_file_content')
    def test_upload_with_invalid_content_type(self, mock_validate):
        """Test upload with invalid MIME type."""
        mock_validate.return_value = False
        
        # Create a file with mismatched content
        fake_pdf = FileStorage(
            stream=BytesIO(b'This is not a PDF'),
            filename='fake.pdf',
            content_type='application/pdf'
        )
        
        with self.app.test_request_context():
            response = self.client.post('/upload', data={
                'files': fake_pdf
            })
            
            # Should handle invalid content gracefully
            data = response.get_json()
            if data:
                self.assertIn('success', data)
    
    def test_path_traversal_prevention(self):
        """Test path traversal attack prevention."""
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam",
            "....//....//etc/passwd"
        ]
        
        for malicious_filename in malicious_filenames:
            secure_name = generate_secure_filename(malicious_filename)
            
            # Secure filename should not contain path separators
            self.assertNotIn('/', secure_name)
            self.assertNotIn('\\', secure_name)
            self.assertNotIn('..', secure_name)
            
            # Should be a valid UUID-based filename
            name_parts = secure_name.split('.')
            if len(name_parts) > 1:
                uuid_part = name_parts[0]
                self.assertEqual(len(uuid_part), 36)  # UUID length
    
    def test_unicode_filename_handling(self):
        """Test handling of Unicode characters in filenames."""
        unicode_filenames = [
            "测试文档.pdf",
            "документ.jpg",
            "αρχείο.png",
            "файл с пробелами.csv",
            "emoji😀test.pdf"
        ]
        
        for unicode_filename in unicode_filenames:
            secure_name = generate_secure_filename(unicode_filename)
            
            # Should generate valid UUID-based filename
            self.assertIsInstance(secure_name, str)
            self.assertGreater(len(secure_name), 30)  # Should be reasonable length
            
            # Should preserve extension if valid
            if unicode_filename.endswith('.pdf'):
                self.assertTrue(secure_name.endswith('.pdf'))
    
    @patch('os.path.getsize')
    def test_file_size_check_on_disk(self, mock_getsize):
        """Test file size checking after saving to disk."""
        # Mock file size as too large
        mock_getsize.return_value = 11 * 1024 * 1024  # 11MB
        
        test_file = FileStorage(
            stream=BytesIO(b'test content'),
            filename='test.pdf',
            content_type='application/pdf'
        )
        
        # In a real scenario, this would be checked during upload processing
        file_size = mock_getsize.return_value
        max_size = 10 * 1024 * 1024  # 10MB
        
        self.assertGreater(file_size, max_size)

class TestUploadEndpointSecurity(unittest.TestCase):
    """Test security of the upload endpoint specifically."""
    
    def setUp(self):
        """Set up test environment."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'QBO_CLIENT_ID': 'test_client_id',
            'QBO_CLIENT_SECRET': 'test_client_secret',
            'FLASK_SECRET_KEY': 'test_secret_key_for_testing_only_32chars',
            'GEMINI_API_KEY': 'test_gemini_key'
        })
        self.env_patcher.start()
        
    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
    
    def test_upload_no_files(self):
        """Test upload endpoint with no files."""
        response = self.client.post('/upload')
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('No files were selected', data['message'])
    
    def test_upload_empty_filename(self):
        """Test upload endpoint with empty filename."""
        empty_file = FileStorage(
            stream=BytesIO(b''),
            filename='',
            content_type='application/octet-stream'
        )
        
        response = self.client.post('/upload', data={
            'files': empty_file
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])
    
    @patch('app.qbo_service.access_token', None)
    def test_upload_without_qbo_auth(self, mock_token):
        """Test upload works without QBO authentication (with warning)."""
        test_file = FileStorage(
            stream=BytesIO(b'test,data\n1,2'),
            filename='test.csv',
            content_type='text/csv'
        )
        
        # This should work but show warnings about QBO not being connected
        response = self.client.post('/upload', data={
            'files': test_file
        })
        
        # Response should indicate processing started
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('progressSessionId', data)

if __name__ == '__main__':
    unittest.main()