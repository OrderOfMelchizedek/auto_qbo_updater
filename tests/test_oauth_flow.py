import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import sys
import json
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import app
from utils.qbo_service import QBOService

class TestOAuthFlow(unittest.TestCase):
    """Test OAuth authentication flow for QuickBooks Online."""
    
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
    
    def test_qbo_status_unauthenticated(self):
        """Test QBO status endpoint when not authenticated."""
        response = self.client.get('/qbo/status')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data['authenticated'])
        self.assertIsNone(data['realmId'])
        self.assertIsNone(data['tokenExpiry'])
        self.assertIn('environment', data)
    
    def test_qbo_auth_status_unauthenticated(self):
        """Test QBO auth status endpoint when not authenticated."""
        response = self.client.get('/qbo/auth-status')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data['authenticated'])
        self.assertIsNone(data['tokenExpiry'])
        self.assertFalse(data['justConnected'])
    
    @patch('src.utils.qbo_service.QBOService.get_authorization_url')
    def test_qbo_authorize_redirect(self, mock_get_auth_url):
        """Test OAuth authorization redirect."""
        mock_auth_url = 'https://appcenter.intuit.com/connect/oauth2?client_id=test'
        mock_get_auth_url.return_value = mock_auth_url
        
        response = self.client.get('/qbo/authorize')
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, mock_auth_url)
        mock_get_auth_url.assert_called_once()
    
    def test_qbo_callback_missing_parameters(self):
        """Test OAuth callback with missing parameters."""
        response = self.client.get('/qbo/callback')
        
        self.assertEqual(response.status_code, 302)  # Redirect to index
        # Should redirect to index page with error
        self.assertIn('/', response.location)
    
    def test_qbo_callback_with_error(self):
        """Test OAuth callback with error parameter."""
        response = self.client.get('/qbo/callback?error=access_denied&error_description=User+denied+access')
        
        self.assertEqual(response.status_code, 302)  # Redirect to index
        self.assertIn('/', response.location)
    
    @patch('src.utils.qbo_service.QBOService.get_tokens')
    @patch('src.utils.qbo_service.QBOService.get_all_customers')
    def test_qbo_callback_success(self, mock_get_customers, mock_get_tokens):
        """Test successful OAuth callback."""
        # Mock successful token exchange
        mock_get_tokens.return_value = True
        mock_get_customers.return_value = [
            {'Id': '1', 'Name': 'Test Customer 1'},
            {'Id': '2', 'Name': 'Test Customer 2'}
        ]
        
        response = self.client.get('/qbo/callback?code=test_auth_code&realmId=123456789')
        
        self.assertEqual(response.status_code, 302)  # Redirect to index
        self.assertIn('/', response.location)
        
        # Verify method calls
        mock_get_tokens.assert_called_once_with('test_auth_code', '123456789')
        mock_get_customers.assert_called_once()
    
    @patch('src.utils.qbo_service.QBOService.get_tokens')
    def test_qbo_callback_token_failure(self, mock_get_tokens):
        """Test OAuth callback when token exchange fails."""
        mock_get_tokens.return_value = False
        
        response = self.client.get('/qbo/callback?code=test_auth_code&realmId=123456789')
        
        self.assertEqual(response.status_code, 302)  # Redirect to index
        self.assertIn('/', response.location)
        mock_get_tokens.assert_called_once_with('test_auth_code', '123456789')
    
    @patch('src.utils.qbo_service.QBOService.get_tokens')
    @patch('src.utils.qbo_service.QBOService.get_all_customers')
    def test_qbo_callback_customer_fetch_failure(self, mock_get_customers, mock_get_tokens):
        """Test OAuth callback when customer fetch fails."""
        from utils.exceptions import QBOAPIException
        
        mock_get_tokens.return_value = True
        mock_get_customers.side_effect = QBOAPIException("API Error", is_user_error=True)
        
        response = self.client.get('/qbo/callback?code=test_auth_code&realmId=123456789')
        
        self.assertEqual(response.status_code, 302)  # Redirect to index
        mock_get_tokens.assert_called_once_with('test_auth_code', '123456789')
        mock_get_customers.assert_called_once()

class TestQBOService(unittest.TestCase):
    """Test QBOService OAuth functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.qbo_service = QBOService(
            client_id='test_client_id',
            client_secret='test_client_secret',
            redirect_uri='http://localhost:5000/qbo/callback',
            environment='sandbox'
        )
    
    def test_get_authorization_url(self):
        """Test authorization URL generation."""
        auth_url = self.qbo_service.get_authorization_url()
        
        self.assertIsInstance(auth_url, str)
        self.assertIn('appcenter.intuit.com', auth_url)
        self.assertIn('client_id=test_client_id', auth_url)
        self.assertIn('redirect_uri=', auth_url)
        self.assertIn('scope=com.intuit.quickbooks.accounting', auth_url)
    
    def test_is_token_valid_no_token(self):
        """Test token validation with no token."""
        self.assertFalse(self.qbo_service.is_token_valid())
    
    def test_is_token_valid_expired_token(self):
        """Test token validation with expired token."""
        # Set expired token
        self.qbo_service.access_token = 'test_token'
        self.qbo_service.token_expires_at = (datetime.now() - timedelta(hours=1)).isoformat()
        
        self.assertFalse(self.qbo_service.is_token_valid())
    
    def test_is_token_valid_valid_token(self):
        """Test token validation with valid token."""
        # Set valid token
        self.qbo_service.access_token = 'test_token'
        self.qbo_service.token_expires_at = (datetime.now() + timedelta(hours=1)).isoformat()
        
        self.assertTrue(self.qbo_service.is_token_valid())
    
    def test_get_token_info_no_token(self):
        """Test get token info with no token."""
        token_info = self.qbo_service.get_token_info()
        
        self.assertIsNone(token_info)
    
    def test_get_token_info_with_token(self):
        """Test get token info with valid token."""
        expires_at = datetime.now() + timedelta(hours=2)
        self.qbo_service.access_token = 'test_token'
        self.qbo_service.token_expires_at = expires_at.isoformat()
        self.qbo_service.realm_id = '123456789'
        
        token_info = self.qbo_service.get_token_info()
        
        self.assertIsNotNone(token_info)
        self.assertEqual(token_info['realm_id'], '123456789')
        self.assertIn('expires_at', token_info)
        self.assertIn('expires_in_hours', token_info)
        self.assertGreater(token_info['expires_in_hours'], 0)
    
    @patch('requests.post')
    def test_get_tokens_success(self, mock_post):
        """Test successful token exchange."""
        # Mock successful token response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 3600,
            'token_type': 'Bearer'
        }
        mock_post.return_value = mock_response
        
        result = self.qbo_service.get_tokens('auth_code', '123456789')
        
        self.assertTrue(result)
        self.assertEqual(self.qbo_service.access_token, 'new_access_token')
        self.assertEqual(self.qbo_service.refresh_token, 'new_refresh_token')
        self.assertEqual(self.qbo_service.realm_id, '123456789')
        self.assertIsNotNone(self.qbo_service.token_expires_at)
    
    @patch('requests.post')
    def test_get_tokens_failure(self, mock_post):
        """Test failed token exchange."""
        # Mock failed token response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': 'invalid_grant',
            'error_description': 'Invalid authorization code'
        }
        mock_post.return_value = mock_response
        
        result = self.qbo_service.get_tokens('invalid_code', '123456789')
        
        self.assertFalse(result)
        self.assertIsNone(self.qbo_service.access_token)
        self.assertIsNone(self.qbo_service.refresh_token)
    
    @patch('requests.post')
    def test_refresh_tokens_success(self, mock_post):
        """Test successful token refresh."""
        # Set initial tokens
        self.qbo_service.refresh_token = 'old_refresh_token'
        
        # Mock successful refresh response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'refreshed_access_token',
            'refresh_token': 'refreshed_refresh_token',
            'expires_in': 3600,
            'token_type': 'Bearer'
        }
        mock_post.return_value = mock_response
        
        result = self.qbo_service.refresh_tokens()
        
        self.assertTrue(result)
        self.assertEqual(self.qbo_service.access_token, 'refreshed_access_token')
        self.assertEqual(self.qbo_service.refresh_token, 'refreshed_refresh_token')

if __name__ == '__main__':
    unittest.main()