"""
Unit tests for QBO blueprint routes.
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
def mock_qbo_service():
    """Create a mock QBO service."""
    mock_service = Mock()
    return mock_service


@pytest.fixture
def sample_donation():
    """Create a sample donation."""
    return {
        'internalId': 'donation_123',
        'Donor Name': 'John Doe',
        'First Name': 'John',
        'Last Name': 'Doe',
        'Gift Amount': '100.00',
        'Check No.': '1234',
        'Gift Date': '2024-01-15',
        'Email': 'john@example.com',
        'Phone': '555-1234',
        'Address - Line 1': '123 Main St',
        'City': 'Anytown',
        'State': 'CA',
        'ZIP': '12345'
    }


@pytest.fixture
def sample_customer():
    """Create a sample QBO customer."""
    return {
        'Id': 'customer-123',
        'DisplayName': 'John Doe',
        'GivenName': 'John',
        'FamilyName': 'Doe',
        'CompanyName': None,
        'PrimaryEmailAddr': {'Address': 'john@example.com'},
        'PrimaryPhone': {'FreeFormNumber': '555-1234'},
        'BillAddr': {
            'Line1': '123 Main St',
            'City': 'Anytown',
            'CountrySubDivisionCode': 'CA',
            'PostalCode': '12345'
        },
        'SyncToken': '0',
        'Active': True
    }


class TestQBORoutes:
    """Test QuickBooks integration routes."""
    
    def test_search_qbo_customer_found(self, client, mock_qbo_service, sample_donation, sample_customer):
        """Test searching for customer that exists."""
        mock_qbo_service.find_customer.return_value = sample_customer
        
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]
            sess['qbo_authenticated'] = True
        
        with patch('routes.qbo.get_qbo_service', return_value=mock_qbo_service):
            response = client.get('/qbo/customer/donation_123')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['found'] is True
            assert data['customer']['id'] == 'customer-123'
            assert data['customer']['displayName'] == 'John Doe'
            assert data['matchConfidence'] == 'High'
            
            # Verify donation was updated
            with client.session_transaction() as sess:
                donation = sess['donations'][0]
                assert donation['qboCustomerId'] == 'customer-123'
                assert donation['qbCustomerStatus'] == 'Found'
                assert donation['matchMethod'] == 'Search'
    
    def test_search_qbo_customer_not_found(self, client, mock_qbo_service, sample_donation):
        """Test searching for customer that doesn't exist."""
        mock_qbo_service.find_customer.return_value = None
        
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]
            sess['qbo_authenticated'] = True
        
        with patch('routes.qbo.get_qbo_service', return_value=mock_qbo_service):
            response = client.get('/qbo/customer/donation_123')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['found'] is False
            assert 'No customer found' in data['message']
            
            # Verify donation was updated
            with client.session_transaction() as sess:
                donation = sess['donations'][0]
                assert donation['qbCustomerStatus'] == 'Not Found'
                assert 'qboCustomerId' not in donation
    
    def test_search_qbo_customer_donation_not_found(self, client):
        """Test searching with invalid donation ID."""
        with client.session_transaction() as sess:
            sess['donations'] = []
            sess['qbo_authenticated'] = True
        
        response = client.get('/qbo/customer/invalid_id')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] == 'Donation not found'
    
    def test_search_qbo_customer_not_authenticated(self, client, sample_donation):
        """Test searching when not authenticated to QBO."""
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]
            sess['qbo_authenticated'] = False
        
        response = client.get('/qbo/customer/donation_123')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'QuickBooks not authenticated'
    
    def test_search_qbo_customer_no_donor_name(self, client, sample_donation):
        """Test searching when donation has no donor name."""
        donation_no_name = sample_donation.copy()
        donation_no_name['Donor Name'] = ''
        
        with client.session_transaction() as sess:
            sess['donations'] = [donation_no_name]
            sess['qbo_authenticated'] = True
        
        response = client.get('/qbo/customer/donation_123')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'No donor name available'
    
    def test_get_all_qbo_customers_success(self, client, mock_qbo_service):
        """Test getting all QBO customers."""
        mock_customers = [
            sample_customer,
            {
                'Id': 'customer-456',
                'DisplayName': 'Jane Smith',
                'GivenName': 'Jane',
                'FamilyName': 'Smith',
                'CompanyName': 'Smith Corp',
                'PrimaryEmailAddr': {'Address': 'jane@example.com'},
                'Active': True
            }
        ]
        mock_qbo_service.get_all_customers.return_value = mock_customers
        
        with client.session_transaction() as sess:
            sess['qbo_authenticated'] = True
        
        with patch('routes.qbo.get_qbo_service', return_value=mock_qbo_service):
            response = client.get('/qbo/customers/all')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 2
            assert len(data['customers']) == 2
            
            # Verify sorting
            assert data['customers'][0]['displayName'] == 'Jane Smith'
            assert data['customers'][1]['displayName'] == 'John Doe'
    
    def test_manual_match_customer_success(self, client, mock_qbo_service, sample_donation, sample_customer):
        """Test manually matching a customer."""
        mock_qbo_service.get_customer_by_id.return_value = sample_customer
        
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]
            sess['qbo_authenticated'] = True
            sess['session_id'] = 'test-session'
        
        with patch('routes.qbo.get_qbo_service', return_value=mock_qbo_service), \
             patch('routes.qbo.log_audit_event') as mock_audit:
            
            response = client.post('/qbo/customer/manual-match/donation_123',
                                 json={'customerId': 'customer-123'},
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['customer']['id'] == 'customer-123'
            
            # Verify donation was updated
            with client.session_transaction() as sess:
                donation = sess['donations'][0]
                assert donation['qboCustomerId'] == 'customer-123'
                assert donation['qbCustomerStatus'] == 'Matched'
                assert donation['matchMethod'] == 'Manual'
                assert donation['matchConfidence'] == 'Manual'
            
            # Verify audit log
            mock_audit.assert_called_once()
            assert mock_audit.call_args[1]['event_type'] == 'qbo_manual_customer_match'
    
    def test_manual_match_customer_not_found_in_qbo(self, client, mock_qbo_service, sample_donation):
        """Test manual match when customer doesn't exist in QBO."""
        mock_qbo_service.get_customer_by_id.return_value = None
        
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]
            sess['qbo_authenticated'] = True
        
        with patch('routes.qbo.get_qbo_service', return_value=mock_qbo_service):
            response = client.post('/qbo/customer/manual-match/donation_123',
                                 json={'customerId': 'invalid-id'},
                                 content_type='application/json')
            
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['error'] == 'Customer not found in QuickBooks'
    
    def test_create_qbo_customer_success(self, client, mock_qbo_service, sample_donation, sample_customer):
        """Test creating a new QBO customer."""
        mock_qbo_service.create_customer.return_value = sample_customer
        
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]
            sess['qbo_authenticated'] = True
            sess['session_id'] = 'test-session'
        
        with patch('routes.qbo.get_qbo_service', return_value=mock_qbo_service), \
             patch('routes.qbo.log_audit_event') as mock_audit:
            
            response = client.post('/qbo/customer/create/donation_123')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['customer']['id'] == 'customer-123'
            
            # Verify create_customer was called with correct data
            mock_qbo_service.create_customer.assert_called_once()
            call_args = mock_qbo_service.create_customer.call_args[0][0]
            assert call_args['DisplayName'] == 'John Doe'
            assert call_args['GivenName'] == 'John'
            assert call_args['FamilyName'] == 'Doe'
            assert call_args['PrimaryEmailAddr']['Address'] == 'john@example.com'
            
            # Verify donation was updated
            with client.session_transaction() as sess:
                donation = sess['donations'][0]
                assert donation['qboCustomerId'] == 'customer-123'
                assert donation['qbCustomerStatus'] == 'Created'
                assert donation['matchMethod'] == 'Created'
            
            # Verify audit log
            mock_audit.assert_called_once()
            assert mock_audit.call_args[1]['event_type'] == 'qbo_customer_created'
    
    def test_create_qbo_customer_with_custom_data(self, client, mock_qbo_service, sample_donation, sample_customer):
        """Test creating customer with custom data."""
        mock_qbo_service.create_customer.return_value = sample_customer
        
        custom_data = {
            'DisplayName': 'Custom Name',
            'Notes': 'Created from donation'
        }
        
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]
            sess['qbo_authenticated'] = True
        
        with patch('routes.qbo.get_qbo_service', return_value=mock_qbo_service):
            response = client.post('/qbo/customer/create/donation_123',
                                 json=custom_data,
                                 content_type='application/json')
            
            assert response.status_code == 200
            
            # Verify custom data was used
            mock_qbo_service.create_customer.assert_called_once_with(custom_data)
    
    def test_update_qbo_customer_success(self, client, mock_qbo_service, sample_donation, sample_customer):
        """Test updating an existing QBO customer."""
        sample_donation['qboCustomerId'] = 'customer-123'
        updated_customer = sample_customer.copy()
        updated_customer['Notes'] = 'Updated'
        mock_qbo_service.update_customer.return_value = updated_customer
        
        update_data = {'Notes': 'Updated from donation'}
        
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]
            sess['qbo_authenticated'] = True
            sess['session_id'] = 'test-session'
        
        with patch('routes.qbo.get_qbo_service', return_value=mock_qbo_service), \
             patch('routes.qbo.log_audit_event') as mock_audit:
            
            response = client.post('/qbo/customer/update/donation_123',
                                 json=update_data,
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify update was called
            mock_qbo_service.update_customer.assert_called_once_with('customer-123', update_data)
            
            # Verify donation was updated
            with client.session_transaction() as sess:
                donation = sess['donations'][0]
                assert donation['qbCustomerStatus'] == 'Updated'
                assert 'lastUpdated' in donation
            
            # Verify audit log
            mock_audit.assert_called_once()
            assert mock_audit.call_args[1]['event_type'] == 'qbo_customer_updated'
    
    def test_update_qbo_customer_no_match(self, client, sample_donation):
        """Test updating when donation has no matched customer."""
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]  # No qboCustomerId
            sess['qbo_authenticated'] = True
        
        response = client.post('/qbo/customer/update/donation_123',
                             json={},
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'No customer matched to this donation'
    
    def test_create_sales_receipt_success(self, client, mock_qbo_service, sample_donation):
        """Test creating a sales receipt."""
        sample_donation['qboCustomerId'] = 'customer-123'
        
        mock_receipt = {
            'Id': 'receipt-456',
            'DocNumber': 'SR-1001',
            'TotalAmt': 100.00
        }
        mock_qbo_service.create_sales_receipt.return_value = mock_receipt
        
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]
            sess['qbo_authenticated'] = True
            sess['session_id'] = 'test-session'
        
        with patch('routes.qbo.get_qbo_service', return_value=mock_qbo_service), \
             patch('routes.qbo.log_audit_event') as mock_audit:
            
            response = client.post('/qbo/sales-receipt/donation_123')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['receipt']['id'] == 'receipt-456'
            assert data['receipt']['docNumber'] == 'SR-1001'
            
            # Verify donation was updated
            with client.session_transaction() as sess:
                donation = sess['donations'][0]
                assert donation['qboSalesReceiptId'] == 'receipt-456'
                assert donation['qboSalesReceiptNumber'] == 'SR-1001'
                assert donation['qboSyncStatus'] == 'Synced'
                assert 'qboSyncDate' in donation
            
            # Verify audit log
            mock_audit.assert_called_once()
            assert mock_audit.call_args[1]['event_type'] == 'qbo_sales_receipt_created'
            assert mock_audit.call_args[1]['details']['amount'] == '100.00'
    
    def test_create_sales_receipt_no_customer(self, client, sample_donation):
        """Test creating receipt when no customer is matched."""
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]  # No qboCustomerId
            sess['qbo_authenticated'] = True
        
        response = client.post('/qbo/sales-receipt/donation_123')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'Customer must be matched before creating sales receipt'
    
    def test_create_sales_receipt_failure(self, client, mock_qbo_service, sample_donation):
        """Test sales receipt creation failure."""
        sample_donation['qboCustomerId'] = 'customer-123'
        mock_qbo_service.create_sales_receipt.return_value = None
        
        with client.session_transaction() as sess:
            sess['donations'] = [sample_donation]
            sess['qbo_authenticated'] = True
        
        with patch('routes.qbo.get_qbo_service', return_value=mock_qbo_service):
            response = client.post('/qbo/sales-receipt/donation_123')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] == 'Failed to create sales receipt'