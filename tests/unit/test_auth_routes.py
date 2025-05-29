"""
Unit tests for auth blueprint routes.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timedelta


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
def mock_qbo_service():
    """Create a mock QBO service."""
    mock_service = Mock()
    mock_service.environment = 'sandbox'
    mock_service.get_access_token.return_value = 'test-access-token'
    mock_service.get_token_info.return_value = {
        'is_valid': True,
        'expires_in_seconds': 3600
    }
    return mock_service


class TestAuthRoutes:
    """Test authentication routes."""
    
    def test_auth_status_authenticated(self, client, mock_qbo_service):
        """Test auth status when authenticated."""
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service):
            with client.session_transaction() as sess:
                sess['qbo_authenticated'] = True
                sess['qbo_company_id'] = 'test-company-123'
                sess['qbo_token_expires_at'] = '2024-12-31T23:59:59'
            
            response = client.get('/qbo/auth-status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['authenticated'] is True
            assert data['company_id'] == 'test-company-123'
            assert data['environment'] == 'sandbox'
            assert data['token_valid'] is True
            assert data['token_expires_in'] == 3600
    
    def test_auth_status_not_authenticated(self, client, mock_qbo_service):
        """Test auth status when not authenticated."""
        mock_qbo_service.get_access_token.return_value = None
        
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service):
            response = client.get('/qbo/auth-status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['authenticated'] is False
            assert data['company_id'] is None
    
    def test_auth_status_invalid_session_token(self, client, mock_qbo_service):
        """Test auth status when session says authenticated but no valid token."""
        mock_qbo_service.get_access_token.return_value = None
        
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service):
            with client.session_transaction() as sess:
                sess['qbo_authenticated'] = True
            
            response = client.get('/qbo/auth-status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['authenticated'] is False  # Should be corrected
            
            # Verify session was updated
            with client.session_transaction() as sess:
                assert sess.get('qbo_authenticated') is False
    
    def test_auth_status_error(self, client):
        """Test auth status error handling."""
        with patch('routes.auth.get_qbo_service', side_effect=Exception("Service error")):
            response = client.get('/qbo/auth-status')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
            assert data['authenticated'] is False
    
    def test_disconnect_success(self, client, mock_qbo_service):
        """Test successful disconnect."""
        mock_qbo_service.redis_client = Mock()
        mock_qbo_service.clear_tokens.return_value = None
        
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service):
            with client.session_transaction() as sess:
                sess['qbo_authenticated'] = True
                sess['qbo_company_id'] = 'test-company'
                sess['qbo_access_token'] = 'test-token'
            
            response = client.post('/qbo/disconnect')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['message'] == 'Disconnected from QuickBooks'
            
            # Verify session was cleared
            with client.session_transaction() as sess:
                assert 'qbo_authenticated' not in sess
                assert 'qbo_company_id' not in sess
                assert 'qbo_access_token' not in sess
    
    def test_disconnect_with_redis_error(self, client, mock_qbo_service):
        """Test disconnect when Redis clear fails."""
        mock_qbo_service.redis_client = Mock()
        mock_qbo_service.clear_tokens.side_effect = Exception("Redis error")
        
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service):
            response = client.post('/qbo/disconnect')
            
            # Should still succeed despite Redis error
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
    
    def test_disconnect_error(self, client):
        """Test disconnect error handling."""
        with patch('routes.auth.get_qbo_service', side_effect=Exception("Service error")):
            response = client.post('/qbo/disconnect')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data
    
    def test_qbo_status_authenticated(self, client, mock_qbo_service):
        """Test QBO status when authenticated."""
        mock_qbo_service.is_authenticated.return_value = True
        mock_qbo_service.get_company_info.return_value = {
            'CompanyName': 'Test Company',
            'Id': 'company-123'
        }
        
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service):
            response = client.get('/qbo/status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['authenticated'] is True
            assert data['environment'] == 'sandbox'
            assert data['company']['name'] == 'Test Company'
            assert data['company']['id'] == 'company-123'
    
    def test_qbo_status_not_authenticated(self, client, mock_qbo_service):
        """Test QBO status when not authenticated."""
        mock_qbo_service.is_authenticated.return_value = False
        
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service):
            response = client.get('/qbo/status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['authenticated'] is False
            assert 'company' not in data
    
    def test_qbo_status_company_info_error(self, client, mock_qbo_service):
        """Test QBO status when company info fetch fails."""
        mock_qbo_service.is_authenticated.return_value = True
        mock_qbo_service.get_company_info.side_effect = Exception("API error")
        
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service):
            response = client.get('/qbo/status')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['authenticated'] is True
            assert 'company_error' in data
            assert 'API error' in data['company_error']
    
    def test_qbo_authorize(self, client, mock_qbo_service):
        """Test QBO authorization redirect."""
        mock_qbo_service.get_auth_url.return_value = 'https://appcenter.intuit.com/connect/oauth2?params'
        
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service):
            response = client.get('/qbo/authorize')
            
            assert response.status_code == 302  # Redirect
            assert response.location == 'https://appcenter.intuit.com/connect/oauth2?params'
    
    def test_qbo_callback_success(self, client, mock_qbo_service):
        """Test successful OAuth callback."""
        mock_qbo_service.exchange_code_for_tokens.return_value = {
            'access_token': 'new-access-token',
            'refresh_token': 'new-refresh-token',
            'expires_at': '2024-12-31T23:59:59'
        }
        
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service), \
             patch('routes.auth.log_audit_event') as mock_audit:
            
            response = client.get('/qbo/callback?code=auth-code-123&realmId=company-456')
            
            assert response.status_code == 302  # Redirect
            assert '/?qbo_connected=true' in response.location
            
            # Verify session was updated
            with client.session_transaction() as sess:
                assert sess['qbo_authenticated'] is True
                assert sess['qbo_company_id'] == 'company-456'
                assert sess['qbo_access_token'] == 'new-access-token'
            
            # Verify audit log
            mock_audit.assert_called_once()
            call_args = mock_audit.call_args[1]
            assert call_args['event_type'] == 'qbo_auth_success'
            assert call_args['details']['company_id'] == 'company-456'
    
    def test_qbo_callback_no_code(self, client):
        """Test OAuth callback with no authorization code."""
        response = client.get('/qbo/callback?error=access_denied&error_description=User+denied')
        
        assert response.status_code == 302
        assert '/?qbo_error=access_denied' in response.location
    
    def test_qbo_callback_token_exchange_failure(self, client, mock_qbo_service):
        """Test OAuth callback when token exchange fails."""
        mock_qbo_service.exchange_code_for_tokens.return_value = None
        
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service):
            response = client.get('/qbo/callback?code=auth-code-123&realmId=company-456')
            
            assert response.status_code == 302
            assert '/?qbo_error=token_exchange_failed' in response.location
    
    def test_qbo_callback_exception(self, client, mock_qbo_service):
        """Test OAuth callback exception handling."""
        mock_qbo_service.exchange_code_for_tokens.side_effect = Exception("Exchange error")
        
        with patch('routes.auth.get_qbo_service', return_value=mock_qbo_service):
            response = client.get('/qbo/callback?code=auth-code-123')
            
            assert response.status_code == 302
            assert '/?qbo_error=Exchange+error' in response.location