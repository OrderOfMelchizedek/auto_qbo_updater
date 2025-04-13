import os
import json
import requests
from typing import Dict, Any, Optional, List
import base64
from urllib.parse import urlencode, quote
import time

class QBOService:
    """Service for interacting with QuickBooks Online API."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, environment: str = 'sandbox'):
        """Initialize the QBO service with OAuth credentials.
        
        Args:
            client_id: QBO Client ID
            client_secret: QBO Client Secret
            redirect_uri: OAuth redirect URI
            environment: 'sandbox' or 'production'
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.environment = environment
        
        # Base URLs for QBO API
        if environment == 'sandbox':
            self.auth_endpoint = 'https://appcenter.intuit.com/connect/oauth2'
            self.token_endpoint = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'
            self.api_base = 'https://sandbox-quickbooks.api.intuit.com/v3/company/'
        else:
            self.auth_endpoint = 'https://appcenter.intuit.com/connect/oauth2'
            self.token_endpoint = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'
            self.api_base = 'https://quickbooks.api.intuit.com/v3/company/'
        
        # OAuth tokens (to be set during authorization flow)
        self.access_token = None
        self.refresh_token = None
        self.realm_id = None
        self.token_expires_at = 0
    
    def get_authorization_url(self) -> str:
        """Get the QBO authorization URL for OAuth flow.
        
        Returns:
            Authorization URL to redirect the user to
        """
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': 'com.intuit.quickbooks.accounting',
            'redirect_uri': self.redirect_uri,
            'state': str(int(time.time()))  # Simple anti-forgery state token
        }
        
        auth_url = f"{self.auth_endpoint}?{urlencode(params)}"
        return auth_url
    
    def get_tokens(self, authorization_code: str, realm_id: str) -> bool:
        """Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: OAuth authorization code from callback
            realm_id: QBO company ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'authorization_code',
                'code': authorization_code,
                'redirect_uri': self.redirect_uri
            }
            
            response = requests.post(self.token_endpoint, headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.realm_id = realm_id
                self.token_expires_at = int(time.time()) + token_data.get('expires_in', 3600)
                return True
            else:
                print(f"Error getting tokens: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            print(f"Exception in get_tokens: {str(e)}")
            return False
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.refresh_token:
            print("No refresh token available")
            return False
        
        try:
            auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token
            }
            
            response = requests.post(self.token_endpoint, headers=headers, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token', self.refresh_token)
                self.token_expires_at = int(time.time()) + token_data.get('expires_in', 3600)
                return True
            else:
                print(f"Error refreshing token: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            print(f"Exception in refresh_access_token: {str(e)}")
            return False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication for QBO API calls.
        
        Returns:
            Dictionary of HTTP headers
        """
        # Check if token is expired (or will expire soon)
        if int(time.time()) >= (self.token_expires_at - 60):
            self.refresh_access_token()
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def find_customer(self, customer_lookup: str) -> Optional[Dict[str, Any]]:
        """Find a customer in QBO by name or other lookup value with enhanced fuzzy matching.
        
        Args:
            customer_lookup: Customer name or other lookup value
            
        Returns:
            Customer data if found, None otherwise
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return None
        
        # Handle empty lookup values
        if not customer_lookup or customer_lookup.strip() == '':
            print("Empty customer lookup value")
            return None
            
        # Sanitize input for SQL injection prevention
        # This is a simple sanitization, QuickBooks API handles more complex cases
        safe_lookup = customer_lookup.replace("'", "''")
        
        try:
            print(f"Finding customer with progressive matching: '{customer_lookup}'")
            
            # Strategy 1: Exact match on DisplayName (highest confidence)
            query = f"SELECT * FROM Customer WHERE DisplayName = '{safe_lookup}'"
            encoded_query = quote(query)
            url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
            
            response = requests.get(url, headers=self._get_auth_headers())
            
            if response.status_code == 200:
                data = response.json()
                if data['QueryResponse'].get('Customer'):
                    print(f"Strategy 1 - Exact match found: {data['QueryResponse']['Customer'][0].get('DisplayName')}")
                    return data['QueryResponse']['Customer'][0]
            
            # Strategy 2: Match on partial DisplayName (contains)
            query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{safe_lookup}%'"
            encoded_query = quote(query)
            url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
            
            response = requests.get(url, headers=self._get_auth_headers())
            
            if response.status_code == 200:
                data = response.json()
                if data['QueryResponse'].get('Customer'):
                    print(f"Strategy 2 - Partial match found: {data['QueryResponse']['Customer'][0].get('DisplayName')}")
                    return data['QueryResponse']['Customer'][0]
            
            # Strategy 3: Try matching after reversing the name parts
            # This handles cases like "John Smith" vs "Smith, John"
            name_parts = safe_lookup.split()
            if len(name_parts) >= 2:
                # Try last name first pattern
                if ',' not in safe_lookup:  # Only if original doesn't have a comma
                    reversed_name = f"{name_parts[-1]}, {' '.join(name_parts[:-1])}"
                    query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{reversed_name}%'"
                    encoded_query = quote(query)
                    url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                    
                    response = requests.get(url, headers=self._get_auth_headers())
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data['QueryResponse'].get('Customer'):
                            print(f"Strategy 3 - Reversed name match found: {data['QueryResponse']['Customer'][0].get('DisplayName')}")
                            return data['QueryResponse']['Customer'][0]
                # Try comma-separated to space-separated conversion
                elif ',' in safe_lookup:  # Handle "Smith, John" to "John Smith" format
                    parts = safe_lookup.split(',')
                    if len(parts) == 2:
                        # Take last name from before comma, first name from after comma, and reverse them
                        space_separated = f"{parts[1].strip()} {parts[0].strip()}"
                        query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{space_separated}%'"
                        encoded_query = quote(query)
                        url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                        
                        response = requests.get(url, headers=self._get_auth_headers())
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data['QueryResponse'].get('Customer'):
                                print(f"Strategy 3b - Comma to space conversion match found: {data['QueryResponse']['Customer'][0].get('DisplayName')}")
                                return data['QueryResponse']['Customer'][0]
            
            # Strategy 4: Try matching on significant parts
            # Remove common tokens like "and", "&", etc.
            significant_parts = []
            skip_tokens = ['and', '&', 'mr', 'mrs', 'ms', 'dr', 'the', 'of', 'for']
            
            # Extract significant tokens
            for part in safe_lookup.lower().replace(',', ' ').replace('.', ' ').split():
                if part not in skip_tokens and len(part) > 1:
                    significant_parts.append(part)
            
            if significant_parts:
                # Sort tokens by length (longer tokens are likely more specific)
                significant_parts.sort(key=len, reverse=True)
                
                # Try to match on the most significant tokens
                for significant_part in significant_parts:
                    if len(significant_part) > 3:  # Only use tokens with more than 3 chars
                        query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{significant_part}%'"
                        encoded_query = quote(query)
                        url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                        
                        response = requests.get(url, headers=self._get_auth_headers())
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data['QueryResponse'].get('Customer'):
                                print(f"Strategy 4 - Significant part match found: {data['QueryResponse']['Customer'][0].get('DisplayName')} (matched on '{significant_part}')")
                                return data['QueryResponse']['Customer'][0]
            
            # Strategy 5: Try matching on email domain
            # This handles organization names vs email domains (e.g., "XYZ Foundation" vs "xyz.org")
            email_part = None
            if '@' in safe_lookup:
                # Extract the domain part of the email
                email_parts = safe_lookup.split('@')
                if len(email_parts) == 2 and '.' in email_parts[1]:
                    domain = email_parts[1]
                    # Get the part before the TLD
                    org_name = domain.split('.')[0]
                    if len(org_name) > 3:  # Only use if meaningful
                        query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{org_name}%'"
                        encoded_query = quote(query)
                        url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                        
                        response = requests.get(url, headers=self._get_auth_headers())
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data['QueryResponse'].get('Customer'):
                                print(f"Strategy 5 - Email domain match found: {data['QueryResponse']['Customer'][0].get('DisplayName')} (matched on '{org_name}')")
                                return data['QueryResponse']['Customer'][0]
            
            # Strategy 6: Try searching by Primary Phone for numeric inputs
            # This is useful if the lookup string is a phone number
            if safe_lookup.replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
                # Format a cleaned phone number (last 10 digits)
                cleaned_phone = ''.join([c for c in safe_lookup if c.isdigit()])[-10:]
                if len(cleaned_phone) >= 7:  # Need at least 7 digits for meaningful phone match
                    query = f"SELECT * FROM Customer WHERE PrimaryPhone LIKE '%{cleaned_phone[-7:]}%'"
                    encoded_query = quote(query)
                    url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                    
                    response = requests.get(url, headers=self._get_auth_headers())
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data['QueryResponse'].get('Customer'):
                            print(f"Strategy 6 - Phone match found: {data['QueryResponse']['Customer'][0].get('DisplayName')} (matched on phone ending in '{cleaned_phone[-7:]}')")
                            return data['QueryResponse']['Customer'][0]
            
            # No match found after all strategies
            print(f"No matching customer found for: '{customer_lookup}' after trying all strategies")
            return None
        
        except Exception as e:
            print(f"Exception in find_customer: {str(e)}")
            return None
    
    def create_customer(self, customer_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new customer in QBO.
        
        Args:
            customer_data: Customer data dictionary
            
        Returns:
            Created customer data if successful, None otherwise
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return None
        
        try:
            url = f"{self.api_base}{self.realm_id}/customer"
            response = requests.post(url, headers=self._get_auth_headers(), json=customer_data)
            
            if response.status_code == 200:
                return response.json()['Customer']
            else:
                print(f"Error creating customer: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            print(f"Exception in create_customer: {str(e)}")
            return None
    
    def update_customer(self, customer_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing customer in QBO.
        
        Args:
            customer_data: Customer data dictionary with Id and SyncToken
            
        Returns:
            Updated customer data if successful, None otherwise
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return None
        
        try:
            url = f"{self.api_base}{self.realm_id}/customer"
            response = requests.post(url, headers=self._get_auth_headers(), json=customer_data)
            
            if response.status_code == 200:
                return response.json()['Customer']
            else:
                print(f"Error updating customer: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            print(f"Exception in update_customer: {str(e)}")
            return None
    
    def create_sales_receipt(self, sales_receipt_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a sales receipt in QBO.
        
        Args:
            sales_receipt_data: Sales receipt data dictionary
            
        Returns:
            Created sales receipt data if successful, None otherwise
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return None
        
        try:
            url = f"{self.api_base}{self.realm_id}/salesreceipt"
            response = requests.post(url, headers=self._get_auth_headers(), json=sales_receipt_data)
            
            if response.status_code == 200:
                return response.json()['SalesReceipt']
            else:
                print(f"Error creating sales receipt: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            print(f"Exception in create_sales_receipt: {str(e)}")
            return None
            
    def get_all_customers(self) -> List[Dict[str, Any]]:
        """Fetch the complete list of customers from QBO.
        
        Returns:
            List of all customer data dictionaries
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO - Missing access_token or realm_id")
            print(f"access_token exists: {self.access_token is not None}")
            print(f"realm_id exists: {self.realm_id is not None}")
            return []
        
        try:
            print("==== STARTING CUSTOMER RETRIEVAL FROM QUICKBOOKS ====")
            print(f"Using realm_id: {self.realm_id}")
            print(f"API Base URL: {self.api_base}")
            print(f"Environment: {self.environment}")
            
            customers = []
            start_position = 1
            max_results = 1000  # QBO API limit per query
            batch_count = 0
            
            while True:
                batch_count += 1
                # Query for a batch of customers
                query = f"SELECT * FROM Customer STARTPOSITION {start_position} MAXRESULTS {max_results}"
                encoded_query = quote(query)
                url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                
                print(f"Batch {batch_count}: Requesting customers at position {start_position}")
                print(f"Request URL: {url}")
                
                # Print auth headers (but mask token for security)
                headers = self._get_auth_headers()
                auth_value = headers.get('Authorization', '')
                if auth_value:
                    masked_token = auth_value[:15] + "..." + auth_value[-5:]
                    print(f"Authorization header: {masked_token}")
                
                response = requests.get(url, headers=headers)
                
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    batch = data['QueryResponse'].get('Customer', [])
                    
                    # If no more customers, break the loop
                    if not batch:
                        print(f"Batch {batch_count}: No more customers found")
                        break
                    
                    # Print first customer info for debugging
                    if batch and len(batch) > 0:
                        first_customer = batch[0]
                        print(f"Sample customer - ID: {first_customer.get('Id')}, Name: {first_customer.get('DisplayName')}")
                        
                    # Add this batch to our collection
                    customers.extend(batch)
                    print(f"Batch {batch_count}: Retrieved {len(batch)} customers (running total: {len(customers)})")
                    
                    # If we got fewer customers than the max, we're done
                    if len(batch) < max_results:
                        print(f"Batch {batch_count}: Less than max results, finished retrieving")
                        break
                        
                    # Otherwise, update the start position for the next batch
                    start_position += max_results
                else:
                    error_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                    print(f"Error fetching customers: {response.status_code}")
                    print(f"Error details: {error_text}")
                    break
            
            print("==== CUSTOMER RETRIEVAL SUMMARY ====")
            print(f"Successfully retrieved {len(customers)} customers in {batch_count} batches")
            
            # Log a few customer names for verification
            if customers:
                print("Sample of retrieved customers:")
                for i, customer in enumerate(customers[:5]):
                    print(f"  {i+1}. {customer.get('DisplayName', 'Unknown')}")
                print("  ...")
                
            return customers
        except Exception as e:
            print(f"Exception in get_all_customers: {str(e)}")
            import traceback
            traceback.print_exc()
            return []