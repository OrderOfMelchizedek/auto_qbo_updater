"""
Unit tests for files blueprint routes.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, ANY
import json
import io
import os
from werkzeug.datastructures import FileStorage
from datetime import datetime


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Create a test client for the Flask app."""
    # Set required environment variables
    monkeypatch.setenv('FLASK_SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-gemini-key')
    monkeypatch.setenv('QBO_CLIENT_ID', 'test-client-id')
    monkeypatch.setenv('QBO_CLIENT_SECRET', 'test-client-secret')
    monkeypatch.setenv('QBO_REDIRECT_URI', 'http://localhost/callback')
    monkeypatch.setenv('UPLOAD_FOLDER', str(tmp_path))
    monkeypatch.setenv('MAX_FILES_PER_UPLOAD', '10')
    
    # Import after setting env vars
    from src.app import app
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = str(tmp_path)
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_file():
    """Create a mock file for upload testing."""
    file_content = b"Test file content"
    file = FileStorage(
        stream=io.BytesIO(file_content),
        filename="test_donation.csv",
        content_type="text/csv"
    )
    return file


@pytest.fixture
def mock_qbo_service():
    """Create a mock QBO service."""
    mock_service = Mock()
    mock_service.find_customer.return_value = {
        'Id': 'customer-123',
        'DisplayName': 'Test Customer'
    }
    return mock_service


@pytest.fixture
def mock_file_processor():
    """Create a mock file processor."""
    mock_processor = Mock()
    mock_processor.process.return_value = [
        {
            'Donor Name': 'John Doe',
            'Gift Amount': '100.00',
            'Check No.': '1234',
            'Gift Date': '2024-01-15'
        }
    ]
    return mock_processor


class TestFilesRoutes:
    """Test file upload and processing routes."""
    
    def test_upload_start_success(self, client):
        """Test starting a new upload session."""
        response = client.post('/upload-start')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'session_id' in data
        
        # Verify session was initialized
        with client.session_transaction() as sess:
            assert sess['session_id'] == data['session_id']
            assert sess['donations'] == []
            assert sess['upload_in_progress'] is True
            assert 'upload_start_time' in sess
    
    def test_upload_start_error(self, client):
        """Test upload start error handling."""
        with patch('uuid.uuid4', side_effect=Exception("UUID error")):
            response = client.post('/upload-start')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
    
    @patch('routes.files.process_files_task')
    @patch('routes.files.ResultStore')
    def test_upload_async_success(self, mock_store_class, mock_task, client, mock_file):
        """Test async file upload."""
        # Mock Celery task
        mock_task_instance = Mock()
        mock_task_instance.id = 'task-123'
        mock_task.delay.return_value = mock_task_instance
        
        # Mock result store
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        
        with patch('routes.files.log_audit_event'):
            # Upload file
            data = {'files': (mock_file, 'test_donation.csv')}
            response = client.post('/upload-async', 
                                 data=data, 
                                 content_type='multipart/form-data')
            
            assert response.status_code == 200
            result = json.loads(response.data)
            assert result['success'] is True
            assert result['task_id'] == 'task-123'
            assert 'session_id' in result
            
            # Verify task was submitted
            mock_task.delay.assert_called_once()
            call_args = mock_task.delay.call_args[1]
            assert len(call_args['file_paths']) == 1
            assert call_args['file_paths'][0]['original_name'] == 'test_donation.csv'
    
    def test_upload_async_no_files(self, client):
        """Test async upload with no files."""
        response = client.post('/upload-async', 
                             data={}, 
                             content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'No files provided'
    
    def test_upload_async_too_many_files(self, client):
        """Test async upload with too many files."""
        # Create 11 mock files (exceeds limit of 10)
        files = []
        for i in range(11):
            file = FileStorage(
                stream=io.BytesIO(b"content"),
                filename=f"file{i}.csv"
            )
            files.append(('files', (file, f"file{i}.csv")))
        
        response = client.post('/upload-async',
                             data=files,
                             content_type='multipart/form-data')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Too many files' in data['error']
    
    @patch('routes.files.get_memory_monitor')
    @patch('routes.files.log_progress')
    @patch('routes.files.log_audit_event')
    def test_upload_sync_success(self, mock_audit, mock_progress, mock_memory_monitor, 
                               client, mock_file, mock_qbo_service, mock_file_processor):
        """Test synchronous file upload."""
        # Mock memory monitor
        mock_monitor = Mock()
        mock_memory_monitor.return_value = mock_monitor
        
        # Mock app context methods
        with patch('flask.current_app.qbo_service', mock_qbo_service), \
             patch('flask.current_app.file_processor', mock_file_processor), \
             patch('flask.current_app.process_single_file') as mock_process, \
             patch('flask.current_app.cleanup_uploaded_file'):
            
            # Mock process_single_file
            mock_process.return_value = {
                'success': True,
                'filename': 'test_donation.csv',
                'donations': [{
                    'Donor Name': 'John Doe',
                    'Gift Amount': '100.00',
                    'Check No.': '1234'
                }],
                'file_path': '/tmp/test.csv',
                'processing_time': 0.5
            }
            
            # Set QBO authenticated
            with client.session_transaction() as sess:
                sess['qbo_authenticated'] = True
            
            # Upload file
            data = {'files': (mock_file, 'test_donation.csv')}
            response = client.post('/upload',
                                 data=data,
                                 content_type='multipart/form-data')
            
            assert response.status_code == 200
            result = json.loads(response.data)
            assert result['success'] is True
            assert result['total_donations'] == 1
            assert len(result['processed_files']) == 1
            assert result['processed_files'][0]['filename'] == 'test_donation.csv'
            assert result['qbo_authenticated'] is True
            
            # Verify memory monitoring
            mock_monitor.log_memory.assert_called()
            mock_monitor.cleanup.assert_called()
    
    def test_upload_sync_with_deduplication(self, client):
        """Test upload with deduplication of donations."""
        with patch('routes.files.get_memory_monitor'), \
             patch('routes.files.log_progress'), \
             patch('routes.files.log_audit_event'), \
             patch('flask.current_app.process_single_file') as mock_process, \
             patch('flask.current_app.cleanup_uploaded_file'), \
             patch('services.deduplication.DeduplicationService.deduplicate_donations') as mock_dedup:
            
            # Set up existing donations in session
            with client.session_transaction() as sess:
                sess['donations'] = [
                    {'Check No.': '1234', 'Gift Amount': '100.00', 'Donor Name': 'John Doe'}
                ]
            
            # Mock process result with duplicate
            mock_process.return_value = {
                'success': True,
                'filename': 'test.csv',
                'donations': [
                    {'Check No.': '1234', 'Gift Amount': '100.00', 'Donor Name': 'John Doe'},
                    {'Check No.': '5678', 'Gift Amount': '200.00', 'Donor Name': 'Jane Smith'}
                ],
                'file_path': '/tmp/test.csv',
                'processing_time': 0.5
            }
            
            # Mock deduplication result
            mock_dedup.return_value = [
                {'Check No.': '1234', 'Gift Amount': '100.00', 'Donor Name': 'John Doe'},
                {'Check No.': '5678', 'Gift Amount': '200.00', 'Donor Name': 'Jane Smith'}
            ]
            
            # Create mock file
            file = FileStorage(
                stream=io.BytesIO(b"content"),
                filename="test.csv"
            )
            
            response = client.post('/upload',
                                 data={'files': (file, 'test.csv')},
                                 content_type='multipart/form-data')
            
            assert response.status_code == 200
            result = json.loads(response.data)
            assert result['success'] is True
            assert result['donations_found'] == 2
            assert result['unique_donations'] == 2
            
            # Verify deduplication was called
            mock_dedup.assert_called_once()
    
    def test_upload_sync_error_handling(self, client, mock_file):
        """Test sync upload error handling."""
        with patch('routes.files.get_memory_monitor') as mock_memory_monitor, \
             patch('routes.files.log_audit_event'):
            
            mock_monitor = Mock()
            mock_memory_monitor.return_value = mock_monitor
            
            # Simulate processing error
            with patch('flask.current_app.process_single_file', 
                      side_effect=Exception("Processing error")):
                
                response = client.post('/upload',
                                     data={'files': (mock_file, 'test.csv')},
                                     content_type='multipart/form-data')
                
                assert response.status_code == 500
                data = json.loads(response.data)
                assert 'error' in data
                
                # Verify cleanup was called
                mock_monitor.cleanup.assert_called()
    
    @patch('routes.files.celery_app')
    @patch('routes.files.ResultStore')
    def test_task_status_success(self, mock_store_class, mock_celery, client):
        """Test getting task status."""
        # Mock Celery result
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_result.result = {
            'donations': [{'id': 1}, {'id': 2}],
            'processed_files': 2
        }
        mock_celery.AsyncResult.return_value = mock_result
        
        # Mock result store
        mock_store = Mock()
        mock_store.get_task_metadata.return_value = {
            'session_id': 'test-session',
            'file_count': 2
        }
        mock_store_class.return_value = mock_store
        
        with client.session_transaction() as sess:
            sess['session_id'] = 'test-session'
        
        response = client.get('/task-status/task-123')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['task_id'] == 'task-123'
        assert data['state'] == 'SUCCESS'
        assert data['status'] == 'Task completed successfully'
        assert 'result' in data
        
        # Verify donations were stored in session
        with client.session_transaction() as sess:
            assert sess['donations'] == [{'id': 1}, {'id': 2}]
    
    def test_task_status_pending(self, client):
        """Test task status for pending task."""
        with patch('routes.files.celery_app') as mock_celery, \
             patch('routes.files.ResultStore') as mock_store_class:
            
            mock_result = Mock()
            mock_result.state = 'PENDING'
            mock_celery.AsyncResult.return_value = mock_result
            
            mock_store = Mock()
            mock_store.get_task_metadata.return_value = {}
            mock_store_class.return_value = mock_store
            
            response = client.get('/task-status/task-123')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['state'] == 'PENDING'
            assert data['status'] == 'Task is waiting to be processed'
    
    def test_task_status_progress(self, client):
        """Test task status with progress updates."""
        with patch('routes.files.celery_app') as mock_celery, \
             patch('routes.files.ResultStore') as mock_store_class:
            
            mock_result = Mock()
            mock_result.state = 'PROGRESS'
            mock_result.info = {
                'current': 5,
                'total': 10,
                'status': 'Processing file 5 of 10'
            }
            mock_celery.AsyncResult.return_value = mock_result
            
            mock_store = Mock()
            mock_store.get_task_metadata.return_value = {}
            mock_store_class.return_value = mock_store
            
            response = client.get('/task-status/task-123')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['state'] == 'PROGRESS'
            assert data['current'] == 5
            assert data['total'] == 10
            assert data['status'] == 'Processing file 5 of 10'
    
    def test_task_status_failure(self, client):
        """Test task status for failed task."""
        with patch('routes.files.celery_app') as mock_celery, \
             patch('routes.files.ResultStore') as mock_store_class:
            
            mock_result = Mock()
            mock_result.state = 'FAILURE'
            mock_result.info = Exception("Task failed")
            mock_celery.AsyncResult.return_value = mock_result
            
            mock_store = Mock()
            mock_store.get_task_metadata.return_value = {}
            mock_store_class.return_value = mock_store
            
            response = client.get('/task-status/task-123')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['state'] == 'FAILURE'
            assert 'Task failed' in data['error']
            assert data['status'] == 'Task failed'