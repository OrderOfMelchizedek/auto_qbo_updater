import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import sys
import json
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.qbo_service import QBOService
from utils.exceptions import QBOAPIException, RetryableException

class TestQBOAPIIntegration(unittest.TestCase):
    """Test QBO API integration functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.qbo_service = QBOService(
            client_id='test_client_id',
            client_secret='test_client_secret',
            redirect_uri='http://localhost:5000/qbo/callback',
            environment='sandbox'
        )
        
        # Set up authenticated state
        self.qbo_service.access_token = 'test_access_token'
        self.qbo_service.realm_id = '123456789'
        self.qbo_service.token_expires_at = (datetime.now().replace(microsecond=0) + 
                                           datetime.timedelta(hours=1)).isoformat()
    
    @patch('requests.get')
    def test_get_all_customers_success(self, mock_get):
        """Test successful customer retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResponse': {
                'Customer': [
                    {'Id': '1', 'Name': 'Customer 1', 'DisplayName': 'Customer 1'},
                    {'Id': '2', 'Name': 'Customer 2', 'DisplayName': 'Customer 2'}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        customers = self.qbo_service.get_all_customers()
        
        self.assertEqual(len(customers), 2)
        self.assertEqual(customers[0]['Id'], '1')
        self.assertEqual(customers[1]['Id'], '2')
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_get_all_customers_empty_response(self, mock_get):
        """Test customer retrieval with empty response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'QueryResponse': {}}
        mock_get.return_value = mock_response
        
        customers = self.qbo_service.get_all_customers()
        
        self.assertEqual(customers, [])
    
    @patch('requests.get')
    def test_get_all_customers_api_error(self, mock_get):
        """Test customer retrieval with API error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'Fault': {
                'Error': [{'Detail': 'Bad Request'}]
            }
        }
        mock_get.return_value = mock_response
        
        with self.assertRaises(QBOAPIException):
            self.qbo_service.get_all_customers()
    
    @patch('requests.get')
    def test_find_customer_success(self, mock_get):
        """Test successful customer search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResponse': {
                'Customer': [
                    {'Id': '1', 'Name': 'John Doe', 'DisplayName': 'John Doe'}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        customer = self.qbo_service.find_customer('John Doe')
        
        self.assertIsNotNone(customer)
        self.assertEqual(customer['Id'], '1')
        self.assertEqual(customer['Name'], 'John Doe')
    
    @patch('requests.get')
    def test_find_customer_not_found(self, mock_get):
        """Test customer search with no results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'QueryResponse': {}}
        mock_get.return_value = mock_response
        
        customer = self.qbo_service.find_customer('Nonexistent Customer')
        
        self.assertIsNone(customer)
    
    def test_escape_query_value(self):
        """Test SQL injection prevention in queries."""
        # Test single quote escaping
        escaped = self.qbo_service._escape_query_value("O'Connor")
        self.assertEqual(escaped, "O''Connor")
        
        # Test backslash escaping
        escaped = self.qbo_service._escape_query_value("Test\\Value")
        self.assertEqual(escaped, "Test\\\\Value")
        
        # Test None handling
        escaped = self.qbo_service._escape_query_value(None)
        self.assertEqual(escaped, "")
        
        # Test empty string
        escaped = self.qbo_service._escape_query_value("")
        self.assertEqual(escaped, "")
        
        # Test normal string
        escaped = self.qbo_service._escape_query_value("Normal String")
        self.assertEqual(escaped, "Normal String")
    
    @patch('requests.post')
    def test_create_customer_success(self, mock_post):
        """Test successful customer creation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResponse': {
                'Customer': [
                    {'Id': '123', 'Name': 'New Customer', 'DisplayName': 'New Customer'}
                ]
            }
        }
        mock_post.return_value = mock_response
        
        customer_data = {
            'DisplayName': 'New Customer',
            'Name': 'New Customer'
        }
        
        result = self.qbo_service.create_customer(customer_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['Id'], '123')
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_create_customer_duplicate_error(self, mock_post):
        """Test customer creation with duplicate name error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'Fault': {
                'Error': [{'Detail': 'Duplicate Name Exists Error'}]
            }
        }
        mock_post.return_value = mock_response
        
        customer_data = {
            'DisplayName': 'Duplicate Customer',
            'Name': 'Duplicate Customer'
        }
        
        with self.assertRaises(QBOAPIException) as context:
            self.qbo_service.create_customer(customer_data)
        
        self.assertIn('duplicate', str(context.exception).lower())
    
    @patch('requests.get')
    def test_find_sales_receipt_success(self, mock_get):
        """Test successful sales receipt search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResponse': {
                'SalesReceipt': [
                    {
                        'Id': '456',
                        'DocNumber': '2024-01-01_CHK123',
                        'TxnDate': '2024-01-01',
                        'CustomerRef': {'value': '1'}
                    }
                ]
            }
        }
        mock_get.return_value = mock_get
        
        receipt = self.qbo_service.find_sales_receipt('CHK123', '2024-01-01', '1')
        
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt['Id'], '456')
    
    @patch('requests.get')
    def test_find_sales_receipt_not_found(self, mock_get):
        """Test sales receipt search with no results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'QueryResponse': {}}
        mock_get.return_value = mock_response
        
        receipt = self.qbo_service.find_sales_receipt('NONEXISTENT', '2024-01-01', '1')
        
        self.assertIsNone(receipt)
    
    @patch('requests.post')
    def test_create_sales_receipt_success(self, mock_post):
        """Test successful sales receipt creation."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResponse': {
                'SalesReceipt': [
                    {
                        'Id': '789',
                        'DocNumber': '2024-01-01_CHK123',
                        'TxnDate': '2024-01-01',
                        'Line': [{'Amount': 100.0}]
                    }
                ]
            }
        }
        mock_post.return_value = mock_response
        
        receipt_data = {
            'CustomerRef': {'value': '1'},
            'TxnDate': '2024-01-01',
            'Line': [{'Amount': 100.0}]
        }
        
        result = self.qbo_service.create_sales_receipt(receipt_data)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['Id'], '789')
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_create_sales_receipt_validation_error(self, mock_post):
        """Test sales receipt creation with validation error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'Fault': {
                'Error': [{'Detail': 'Required field missing'}]
            }
        }
        mock_post.return_value = mock_response
        
        receipt_data = {
            'CustomerRef': {'value': '1'},
            # Missing required fields
        }
        
        with self.assertRaises(QBOAPIException):
            self.qbo_service.create_sales_receipt(receipt_data)
    
    @patch('requests.get')
    def test_get_all_items_success(self, mock_get):
        """Test successful items retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResponse': {
                'Item': [
                    {'Id': '1', 'Name': 'Donation', 'Type': 'Service'},
                    {'Id': '2', 'Name': 'Fee', 'Type': 'Service'}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        items = self.qbo_service.get_all_items()
        
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['Name'], 'Donation')
    
    @patch('requests.get')
    def test_get_all_accounts_success(self, mock_get):
        """Test successful accounts retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResponse': {
                'Account': [
                    {'Id': '1', 'Name': 'Checking', 'AccountType': 'Bank'},
                    {'Id': '2', 'Name': 'Revenue', 'AccountType': 'Income'}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        accounts = self.qbo_service.get_all_accounts()
        
        self.assertEqual(len(accounts), 2)
        self.assertEqual(accounts[0]['Name'], 'Checking')
    
    @patch('requests.get')
    def test_get_all_payment_methods_success(self, mock_get):
        """Test successful payment methods retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'QueryResponse': {
                'PaymentMethod': [
                    {'Id': '1', 'Name': 'Check'},
                    {'Id': '2', 'Name': 'Cash'}
                ]
            }
        }
        mock_get.return_value = mock_response
        
        payment_methods = self.qbo_service.get_all_payment_methods()
        
        self.assertEqual(len(payment_methods), 2)
        self.assertEqual(payment_methods[0]['Name'], 'Check')
    
    @patch('requests.get')
    def test_rate_limit_handling(self, mock_get):
        """Test rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}
        mock_get.return_value = mock_response
        
        with self.assertRaises(RetryableException):
            self.qbo_service.get_all_customers()
    
    @patch('requests.get')
    def test_server_error_handling(self, mock_get):
        """Test server error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_get.return_value = mock_response
        
        with self.assertRaises(RetryableException):
            self.qbo_service.get_all_customers()
    
    def test_authentication_required(self):
        """Test that methods require authentication."""
        # Remove authentication
        self.qbo_service.access_token = None
        
        with self.assertRaises(QBOAPIException) as context:
            self.qbo_service.get_all_customers()
        
        self.assertIn('not authenticated', str(context.exception).lower())
    
    @patch('requests.get')
    def test_token_expiry_handling(self, mock_get):
        """Test handling of expired tokens."""
        # Set expired token
        self.qbo_service.token_expires_at = (datetime.now() - 
                                           datetime.timedelta(hours=1)).isoformat()
        
        with self.assertRaises(QBOAPIException) as context:
            self.qbo_service.get_all_customers()
        
        self.assertIn('expired', str(context.exception).lower())
    
    @patch('requests.get')
    def test_connection_error_handling(self, mock_get):
        """Test connection error handling."""
        mock_get.side_effect = ConnectionError("Connection failed")
        
        with self.assertRaises(RetryableException):
            self.qbo_service.get_all_customers()
    
    @patch('requests.get')
    def test_timeout_error_handling(self, mock_get):
        """Test timeout error handling."""
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout("Request timed out")
        
        with self.assertRaises(RetryableException):
            self.qbo_service.get_all_customers()

class TestQBOServiceConfiguration(unittest.TestCase):
    """Test QBO service configuration and initialization."""
    
    def test_sandbox_environment(self):
        """Test sandbox environment configuration."""
        qbo_service = QBOService(
            client_id='test_id',
            client_secret='test_secret',
            redirect_uri='http://localhost:5000/callback',
            environment='sandbox'
        )
        
        self.assertEqual(qbo_service.environment, 'sandbox')
        self.assertIn('sandbox', qbo_service.base_url)
    
    def test_production_environment(self):
        """Test production environment configuration."""
        qbo_service = QBOService(
            client_id='test_id',
            client_secret='test_secret',
            redirect_uri='http://localhost:5000/callback',
            environment='production'
        )
        
        self.assertEqual(qbo_service.environment, 'production')
        self.assertNotIn('sandbox', qbo_service.base_url)
    
    def test_invalid_environment(self):
        """Test invalid environment handling."""
        with self.assertRaises(ValueError):
            QBOService(
                client_id='test_id',
                client_secret='test_secret',
                redirect_uri='http://localhost:5000/callback',
                environment='invalid'
            )

if __name__ == '__main__':
    unittest.main()