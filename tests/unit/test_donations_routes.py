"""
Unit tests for donations blueprint routes.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime


@pytest.fixture
def client(monkeypatch):
    """Create a test client for the Flask app."""
    # Set required environment variables
    monkeypatch.setenv('FLASK_SECRET_KEY', 'test-secret-key')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-gemini-key')
    monkeypatch.setenv('QBO_CLIENT_ID', 'test-client-id')
    monkeypatch.setenv('QBO_CLIENT_SECRET', 'test-client-secret')
    monkeypatch.setenv('QBO_REDIRECT_URI', 'http://localhost/callback')
    
    # Import after setting env vars
    from src.app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_donations():
    """Create sample donation data."""
    return [
        {
            'internalId': 'donation_0',
            'Donor Name': 'John Doe',
            'Gift Amount': '100.00',
            'Check No.': '1234',
            'Gift Date': '2024-01-15',
            'qbCustomerStatus': 'Matched',
            'qboCustomerId': 'customer-123'
        },
        {
            'internalId': 'donation_1',
            'Donor Name': 'Jane Smith',
            'Gift Amount': '200.00',
            'Check No.': '5678',
            'Gift Date': '2024-01-16',
            'qbCustomerStatus': 'New'
        },
        {
            'internalId': 'donation_2',
            'Donor Name': 'Bob Johnson',
            'Gift Amount': '150.00',
            'Check No.': '9012',
            'Gift Date': '2024-01-17',
            'qbCustomerStatus': 'Matched',
            'qboCustomerId': 'customer-456'
        }
    ]


class TestDonationsRoutes:
    """Test donation CRUD routes."""
    
    def test_get_donations_success(self, client, sample_donations):
        """Test getting all donations."""
        with client.session_transaction() as sess:
            sess['donations'] = sample_donations
            sess['session_id'] = 'test-session-123'
        
        response = client.get('/donations')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 3
        assert len(data['donations']) == 3
        assert data['total_amount'] == '450.00'
        assert data['matched_customers'] == 2
        assert data['session_id'] == 'test-session-123'
    
    def test_get_donations_empty(self, client):
        """Test getting donations when none exist."""
        response = client.get('/donations')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 0
        assert data['donations'] == []
        assert data['total_amount'] == '0.00'
        assert data['matched_customers'] == 0
    
    def test_get_donations_invalid_amounts(self, client):
        """Test getting donations with invalid amounts."""
        donations = [
            {'Gift Amount': '100.00'},
            {'Gift Amount': None},
            {'Gift Amount': 'invalid'},
            {'Gift Amount': '50.50'}
        ]
        
        with client.session_transaction() as sess:
            sess['donations'] = donations
        
        response = client.get('/donations')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['total_amount'] == '150.50'  # Only valid amounts
    
    def test_get_donations_error(self, client):
        """Test error handling in get donations."""
        with patch('flask.session.get', side_effect=Exception("Session error")):
            response = client.get('/donations')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_update_donation_success(self, client, sample_donations):
        """Test updating a specific donation."""
        with client.session_transaction() as sess:
            sess['donations'] = sample_donations.copy()
            sess['session_id'] = 'test-session'
        
        with patch('routes.donations.log_audit_event') as mock_audit:
            update_data = {
                'Gift Amount': '125.00',
                'Memo': 'Updated memo'
            }
            
            response = client.put('/donations/donation_1',
                                json=update_data,
                                content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['donation']['Gift Amount'] == '125.00'
            assert data['donation']['Memo'] == 'Updated memo'
            
            # Verify audit log
            mock_audit.assert_called_once()
            call_args = mock_audit.call_args[1]
            assert call_args['event_type'] == 'donation_updated'
            assert call_args['details']['donation_id'] == 'donation_1'
            assert 'Gift Amount' in call_args['details']['updated_fields']
    
    def test_update_donation_not_found(self, client, sample_donations):
        """Test updating non-existent donation."""
        with client.session_transaction() as sess:
            sess['donations'] = sample_donations
        
        response = client.put('/donations/invalid_id',
                            json={'Gift Amount': '100'},
                            content_type='application/json')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Donation not found'
    
    def test_update_donation_error(self, client):
        """Test error handling in update donation."""
        with patch('flask.session.get', side_effect=Exception("Session error")):
            response = client.put('/donations/donation_1',
                                json={},
                                content_type='application/json')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_remove_invalid_donations_success(self, client):
        """Test removing invalid donations."""
        donations = [
            {'internalId': '1', 'isInvalid': True},
            {'internalId': '2', 'isInvalid': False},
            {'internalId': '3'},  # No isInvalid flag
            {'internalId': '4', 'isInvalid': True}
        ]
        
        with client.session_transaction() as sess:
            sess['donations'] = donations
            sess['session_id'] = 'test-session'
        
        with patch('routes.donations.log_audit_event') as mock_audit:
            response = client.post('/donations/remove-invalid')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['removed_count'] == 2
            assert data['remaining_count'] == 2
            
            # Verify session was updated
            with client.session_transaction() as sess:
                assert len(sess['donations']) == 2
                assert all(not d.get('isInvalid', False) for d in sess['donations'])
            
            # Verify audit log
            mock_audit.assert_called_once()
            assert mock_audit.call_args[1]['details']['removed_count'] == 2
    
    def test_remove_invalid_donations_none_invalid(self, client):
        """Test removing when no donations are invalid."""
        donations = [
            {'internalId': '1', 'isInvalid': False},
            {'internalId': '2'}
        ]
        
        with client.session_transaction() as sess:
            sess['donations'] = donations
        
        response = client.post('/donations/remove-invalid')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['removed_count'] == 0
        assert data['remaining_count'] == 2
    
    def test_update_session_donations_success(self, client):
        """Test bulk updating session donations."""
        new_donations = [
            {'internalId': '1', 'Donor Name': 'New Donor 1'},
            {'internalId': '2', 'Donor Name': 'New Donor 2'}
        ]
        
        with patch('routes.donations.log_audit_event') as mock_audit:
            response = client.post('/donations/update-session',
                                 json={'donations': new_donations},
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 2
            
            # Verify session was updated
            with client.session_transaction() as sess:
                assert sess['donations'] == new_donations
            
            # Verify audit log
            mock_audit.assert_called_once()
            assert mock_audit.call_args[1]['details']['donation_count'] == 2
            assert mock_audit.call_args[1]['details']['action'] == 'bulk_update'
    
    def test_update_session_donations_invalid_format(self, client):
        """Test bulk update with invalid data format."""
        response = client.post('/donations/update-session',
                             json={'donations': 'not-a-list'},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Invalid donation data format'
    
    def test_update_session_donations_empty(self, client):
        """Test bulk update with empty donations list."""
        response = client.post('/donations/update-session',
                             json={'donations': []},
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 0
    
    @patch('routes.donations.get_progress_messages')
    def test_progress_stream(self, mock_get_progress, client):
        """Test progress streaming endpoint."""
        # Mock progress messages
        mock_get_progress.side_effect = [
            # First call
            [
                {'message': 'Processing...', 'progress': 50, 'index': 0}
            ],
            # Second call
            [
                {'message': 'Complete!', 'progress': 100, 'index': 1, 'complete': True}
            ]
        ]
        
        response = client.get('/progress-stream/test-session')
        
        assert response.status_code == 200
        assert response.content_type == 'text/event-stream'
        
        # Get response data
        data = response.get_data(as_text=True)
        events = data.strip().split('\n\n')
        
        # Should have at least 3 events (connection, progress, complete)
        assert len(events) >= 3
        
        # Parse first event (connection)
        first_event = events[0]
        assert 'data: ' in first_event
        event_data = json.loads(first_event.replace('data: ', ''))
        assert event_data['message'] == 'Connected to progress stream'
        assert event_data['progress'] == 0
        
        # Verify mock was called
        assert mock_get_progress.call_count >= 2