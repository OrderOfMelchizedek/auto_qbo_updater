import os
import json
import requests
from typing import Dict, Any, Optional, List
import base64
from urllib.parse import urlencode, quote
import time
import logging
import threading
from functools import lru_cache
from datetime import datetime, timedelta

# Import custom exceptions and retry logic
try:
    from .exceptions import QBOAPIException, RetryableException
    from .retry import retry_on_failure, exponential_backoff
except ImportError:
    # For standalone testing
    from exceptions import QBOAPIException, RetryableException
    from retry import retry_on_failure, exponential_backoff

# Configure logger
logger = logging.getLogger(__name__)

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
        
        # Token persistence (for future implementation)
        # TODO: Implement token storage (database or secure file storage)
        
        # Performance optimization: Customer caching
        self._customer_cache = {}
        self._cache_timestamp = None
        self._cache_lock = threading.Lock()
        self._cache_ttl = 300  # 5 minutes cache TTL
    
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
    
    @retry_on_failure(max_attempts=3, exceptions=(requests.RequestException, QBOAPIException))
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
            
            response = requests.post(self.token_endpoint, headers=headers, data=data, timeout=30)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.realm_id = realm_id
                self.token_expires_at = int(time.time()) + token_data.get('expires_in', 3600)
                logger.info("Successfully obtained QBO access tokens")
                return True
            else:
                logger.error(f"Failed to get QBO tokens: {response.status_code} - {response.text}")
                raise QBOAPIException(
                    f"Failed to exchange authorization code",
                    status_code=response.status_code,
                    response_text=response.text
                )
        
        except requests.RequestException as e:
            logger.error(f"Network error getting QBO tokens: {str(e)}")
            raise QBOAPIException(
                f"Network error while getting tokens: {str(e)}",
                status_code=None,
                response_text=None,
                user_message="Unable to connect to QuickBooks. Please check your internet connection."
            )
        except QBOAPIException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_tokens: {str(e)}")
            raise QBOAPIException(
                f"Unexpected error: {str(e)}",
                user_message="An unexpected error occurred. Please try again."
            )
    
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
    
    def is_token_valid(self) -> bool:
        """Check if the current access token is valid.
        
        Returns:
            True if token exists and not expired, False otherwise
        """
        if not self.access_token:
            return False
        
        # Check if token is expired (with 60 second buffer)
        return int(time.time()) < (self.token_expires_at - 60)
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get information about current token status.
        
        Returns:
            Dictionary with token status information
        """
        return {
            'has_access_token': bool(self.access_token),
            'has_refresh_token': bool(self.refresh_token),
            'realm_id': self.realm_id,
            'expires_at': self.token_expires_at,
            'expires_in_seconds': max(0, self.token_expires_at - int(time.time())),
            'is_valid': self.is_token_valid()
        }
    
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
    
    def _escape_query_value(self, value: str) -> str:
        """Properly escape a value for use in QuickBooks API queries.
        
        QuickBooks API uses SQL-like syntax but requires specific escaping:
        - Single quotes are escaped by doubling them
        - Backslashes need to be escaped
        - Percent signs need to be escaped for LIKE queries
        
        Args:
            value: The value to escape
            
        Returns:
            Properly escaped value safe for QuickBooks queries
        """
        if not value:
            return ''
        
        # First, handle backslashes (must be done first)
        escaped = value.replace('\\', '\\\\')
        
        # Then handle single quotes
        escaped = escaped.replace("'", "''")
        
        # Note: % and _ are wildcards in LIKE queries and should not be escaped
        # unless we want to search for literal % or _ characters
        
        return escaped
    
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
            logger.warning("Empty customer lookup value")
            return None
        
        # Try cache first for performance
        cached_customer = self.get_cached_customer(customer_lookup)
        if cached_customer:
            logger.info(f"Found customer '{customer_lookup}' in cache: {cached_customer.get('DisplayName')}")
            return cached_customer
            
        # Properly escape the lookup value
        safe_lookup = self._escape_query_value(customer_lookup)
        
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
                    escaped_reversed = self._escape_query_value(reversed_name)
                    query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{escaped_reversed}%'"
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
                        escaped_space_separated = self._escape_query_value(space_separated)
                        query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{escaped_space_separated}%'"
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
                        escaped_part = self._escape_query_value(significant_part)
                        query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{escaped_part}%'"
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
                        escaped_org_name = self._escape_query_value(org_name)
                        query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{escaped_org_name}%'"
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
                    escaped_phone = self._escape_query_value(cleaned_phone[-7:])
                    query = f"SELECT * FROM Customer WHERE PrimaryPhone LIKE '%{escaped_phone}%'"
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
    
    def find_sales_receipt(self, check_no: str, check_date: str, customer_id: str) -> Optional[Dict[str, Any]]:
        """Find existing sales receipt by check number, date, and customer.
        
        Args:
            check_no: Check number to search for
            check_date: Check date (YYYY-MM-DD format)
            customer_id: QBO Customer ID
            
        Returns:
            Sales receipt data if found, None otherwise
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return None
        
        try:
            # Query for sales receipts matching the criteria
            # Using PaymentRefNum for check number and CustomerRef for customer
            escaped_check_no = self._escape_query_value(check_no)
            escaped_date = self._escape_query_value(check_date)
            escaped_customer_id = self._escape_query_value(customer_id)
            
            query = f"SELECT * FROM SalesReceipt WHERE PaymentRefNum = '{escaped_check_no}' AND TxnDate = '{escaped_date}' AND CustomerRef = '{escaped_customer_id}'"
            encoded_query = quote(query)
            url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
            
            response = requests.get(url, headers=self._get_auth_headers())
            
            if response.status_code == 200:
                data = response.json()
                if data['QueryResponse'].get('SalesReceipt'):
                    receipts = data['QueryResponse']['SalesReceipt']
                    print(f"Found {len(receipts)} matching sales receipt(s)")
                    return receipts[0] if receipts else None
            else:
                print(f"Error querying sales receipts: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            print(f"Exception in find_sales_receipt: {str(e)}")
            return None
    
    def create_sales_receipt(self, sales_receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a sales receipt in QBO with enhanced error handling.
        
        Args:
            sales_receipt_data: Sales receipt data dictionary
            
        Returns:
            Created sales receipt data if successful, or error details
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return {"error": True, "message": "Not authenticated with QBO"}
        
        try:
            url = f"{self.api_base}{self.realm_id}/salesreceipt"
            response = requests.post(url, headers=self._get_auth_headers(), json=sales_receipt_data)
            
            if response.status_code == 200:
                return response.json()['SalesReceipt']
            else:
                error_data = {"error": True, "message": "Error creating sales receipt"}
                
                # Parse error response to identify specific issues
                try:
                    error_json = response.json()
                    if 'Fault' in error_json:
                        # Get error details from response
                        error_detail = error_json['Fault'].get('Error', [{}])[0].get('Detail', '')
                        error_message = error_json['Fault'].get('Error', [{}])[0].get('Message', '')
                        error_code = error_json['Fault'].get('Error', [{}])[0].get('code', '')
                        
                        # Add to error data
                        error_data['detail'] = error_detail
                        error_data['message'] = error_message
                        error_data['code'] = error_code
                        
                        # Log the full error for debugging
                        print(f"QBO Error Response: {error_json}")
                        
                        # Check for specific reference errors
                        if "Invalid Reference Id" in error_message:
                            # Account reference errors - multiple possible error formats
                            if "Accounts element id" in error_detail or "Account id" in error_detail:
                                import re
                                # Try different regex patterns for account errors
                                account_match = re.search(r"Accounts element id (\d+)", error_detail)
                                if not account_match:
                                    account_match = re.search(r"Account id (\d+)", error_detail)
                                
                                if account_match:
                                    account_id = account_match.group(1)
                                    error_data['setupType'] = 'account'
                                    error_data['invalidId'] = account_id
                                    error_data['requiresSetup'] = True
                                    print(f"Detected invalid account reference: {account_id}")
                            
                            # Item reference errors - multiple possible error formats
                            elif "Item elements id" in error_detail or "Item elements Id" in error_detail or "Item id" in error_detail:
                                import re
                                # Try different regex patterns for item errors
                                item_match = re.search(r"Item elements id (\d+)", error_detail)
                                if not item_match:
                                    item_match = re.search(r"Item elements Id (\d+)", error_detail)
                                if not item_match:
                                    item_match = re.search(r"Item id (\d+)", error_detail)
                                
                                if item_match:
                                    item_id = item_match.group(1)
                                    error_data['setupType'] = 'item'
                                    error_data['invalidId'] = item_id
                                    error_data['requiresSetup'] = True
                                    print(f"Detected invalid item reference: {item_id}")
                            
                            # Payment method reference errors
                            elif "PaymentMethod id" in error_detail:
                                # Try to extract the payment method ID from the error
                                import re
                                payment_method_match = re.search(r"PaymentMethod id (\w+)", error_detail)
                                payment_method_id = payment_method_match.group(1) if payment_method_match else 'CHECK'
                                
                                error_data['setupType'] = 'paymentMethod'
                                error_data['invalidId'] = payment_method_id
                                error_data['requiresSetup'] = True
                                print(f"Detected invalid payment method reference: {payment_method_id}")
                        
                        # Handle validation errors (non-reference errors)
                        elif "Object is not valid" in error_message:
                            error_data['validationError'] = True
                            # Try to extract the validation details
                            validation_details = []
                            try:
                                if 'Object validation failed' in error_detail:
                                    # Parse validation failures
                                    validation_lines = error_detail.split('\n')
                                    for line in validation_lines:
                                        if ':' in line and line.strip():
                                            validation_details.append(line.strip())
                            except Exception:
                                pass
                            
                            error_data['validationDetails'] = validation_details
                            print(f"Detected validation error: {validation_details}")
                        
                        # Check for duplicate document number
                        elif "Duplicate" in error_message and "DocNumber" in error_detail:
                            error_data['duplicateError'] = True
                            error_data['duplicateField'] = "DocNumber"
                            print("Detected duplicate document number error")
                except Exception as parse_error:
                    print(f"Error parsing QBO error response: {str(parse_error)}")
                    import traceback
                    traceback.print_exc()
                    
                print(f"Error creating sales receipt: {error_data}")
                return error_data
        
        except Exception as e:
            print(f"Exception in create_sales_receipt: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": True, "message": str(e)}
    
    def _is_cache_valid(self) -> bool:
        """Check if customer cache is still valid.
        
        Returns:
            True if cache is valid, False otherwise
        """
        if not self._cache_timestamp:
            return False
        
        cache_age = datetime.now().timestamp() - self._cache_timestamp
        return cache_age < self._cache_ttl
    
    def _update_customer_cache(self, customers: List[Dict[str, Any]]) -> None:
        """Update the customer cache with new data.
        
        Args:
            customers: List of customer dictionaries
        """
        with self._cache_lock:
            self._customer_cache = {
                customer.get('DisplayName', '').lower(): customer
                for customer in customers
                if customer.get('DisplayName')
            }
            # Also cache by ID for quick lookups
            for customer in customers:
                if customer.get('Id'):
                    self._customer_cache[f"id_{customer['Id']}"] = customer
            
            self._cache_timestamp = datetime.now().timestamp()
            logger.info(f"Updated customer cache with {len(customers)} customers")
    
    def get_cached_customer(self, lookup_value: str) -> Optional[Dict[str, Any]]:
        """Get customer from cache by name or ID.
        
        Args:
            lookup_value: Customer name or ID to lookup
            
        Returns:
            Customer data if found in cache, None otherwise
        """
        if not self._is_cache_valid():
            return None
            
        with self._cache_lock:
            # Try exact match first
            customer = self._customer_cache.get(lookup_value.lower())
            if customer:
                return customer
            
            # Try partial match for names
            lookup_lower = lookup_value.lower()
            for cached_name, customer in self._customer_cache.items():
                if not cached_name.startswith('id_') and lookup_lower in cached_name:
                    return customer
            
            return None
    
    def clear_customer_cache(self) -> None:
        """Clear the customer cache."""
        with self._cache_lock:
            self._customer_cache.clear()
            self._cache_timestamp = None
            logger.info("Customer cache cleared")
            
    def get_all_customers(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Fetch the complete list of customers from QBO.
        
        Args:
            use_cache: Whether to use cached data if available
        
        Returns:
            List of all customer data dictionaries
        """
        # Check cache first if enabled
        if use_cache and self._is_cache_valid():
            with self._cache_lock:
                cached_customers = [customer for key, customer in self._customer_cache.items() 
                                  if not key.startswith('id_')]
                if cached_customers:
                    logger.info(f"Returning {len(cached_customers)} customers from cache")
                    return cached_customers
        
        if not self.access_token or not self.realm_id:
            logger.error("Not authenticated with QBO - Missing access_token or realm_id")
            raise QBOAPIException("QuickBooks not authenticated", is_user_error=True)
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
            
            logger.info(f"Successfully retrieved {len(customers)} customers in {batch_count} batches")
            
            # Log a few customer names for verification
            if customers:
                logger.debug("Sample of retrieved customers:")
                for i, customer in enumerate(customers[:5]):
                    logger.debug(f"  {i+1}. {customer.get('DisplayName', 'Unknown')}")
            
            # Cache the results if we have customers
            if use_cache and customers:
                self._update_customer_cache(customers)
                
            return customers
        except Exception as e:
            print(f"Exception in get_all_customers: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
            
    def create_account(self, account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new account in QBO.
        
        Args:
            account_data: Account data dictionary with required fields:
                - Name: Account name
                - AccountType: Account type (e.g., Bank, Other Current Asset)
                - AccountSubType: Optional sub-type
            
        Returns:
            Created account data if successful, None otherwise
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return None
        
        try:
            # Make sure required fields are present
            if 'Name' not in account_data or 'AccountType' not in account_data:
                print("Missing required fields for account creation")
                return None
                
            url = f"{self.api_base}{self.realm_id}/account"
            response = requests.post(url, headers=self._get_auth_headers(), json=account_data)
            
            if response.status_code == 200:
                account = response.json().get('Account')
                print(f"Successfully created account: {account.get('Name')} (ID: {account.get('Id')})")
                return account
            else:
                print(f"Error creating account: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            print(f"Exception in create_account: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_item(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new item (product/service) in QBO.
        
        Args:
            item_data: Item data dictionary with required fields:
                - Name: Item name
                - Type: Service, Inventory, etc.
                - IncomeAccountRef: Reference to income account
            
        Returns:
            Created item data if successful, None otherwise
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return None
        
        try:
            # Make sure required fields are present
            if 'Name' not in item_data or 'Type' not in item_data:
                print("Missing required fields for item creation")
                return None
                
            # Default to Service type if not specified
            if 'Type' not in item_data:
                item_data['Type'] = 'Service'
                
            # Default to Non-inventory if not specified
            if 'Type' == 'Item' and 'ItemType' not in item_data:
                item_data['ItemType'] = 'Non-inventory'
                
            url = f"{self.api_base}{self.realm_id}/item"
            response = requests.post(url, headers=self._get_auth_headers(), json=item_data)
            
            if response.status_code == 200:
                item = response.json().get('Item')
                print(f"Successfully created item: {item.get('Name')} (ID: {item.get('Id')})")
                return item
            else:
                print(f"Error creating item: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            print(f"Exception in create_item: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_payment_method(self, payment_method_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new payment method in QBO.
        
        Args:
            payment_method_data: Payment method data dictionary with required fields:
                - Name: Payment method name
            
        Returns:
            Created payment method data if successful, None otherwise
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return None
        
        try:
            # Make sure required fields are present
            if 'Name' not in payment_method_data:
                print("Missing required Name field for payment method creation")
                return None
                
            url = f"{self.api_base}{self.realm_id}/paymentmethod"
            response = requests.post(url, headers=self._get_auth_headers(), json=payment_method_data)
            
            if response.status_code == 200:
                payment_method = response.json().get('PaymentMethod')
                print(f"Successfully created payment method: {payment_method.get('Name')} (ID: {payment_method.get('Id')})")
                return payment_method
            else:
                print(f"Error creating payment method: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            print(f"Exception in create_payment_method: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def get_all_items(self) -> List[Dict[str, Any]]:
        """Fetch the complete list of items/products/services from QBO.
        
        Returns:
            List of all item data dictionaries
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO - Missing access_token or realm_id")
            return []
        
        try:
            print("==== STARTING ITEM RETRIEVAL FROM QUICKBOOKS ====")
            
            items = []
            start_position = 1
            max_results = 1000  # QBO API limit per query
            batch_count = 0
            
            while True:
                batch_count += 1
                # Query for a batch of items
                query = f"SELECT * FROM Item STARTPOSITION {start_position} MAXRESULTS {max_results}"
                encoded_query = quote(query)
                url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                
                print(f"Batch {batch_count}: Requesting items at position {start_position}")
                
                response = requests.get(url, headers=self._get_auth_headers())
                
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    batch = data['QueryResponse'].get('Item', [])
                    
                    # If no more items, break the loop
                    if not batch:
                        print(f"Batch {batch_count}: No more items found")
                        break
                    
                    # Add this batch to our collection
                    items.extend(batch)
                    print(f"Batch {batch_count}: Retrieved {len(batch)} items (running total: {len(items)})")
                    
                    # If we got fewer items than the max, we're done
                    if len(batch) < max_results:
                        print(f"Batch {batch_count}: Less than max results, finished retrieving")
                        break
                        
                    # Otherwise, update the start position for the next batch
                    start_position += max_results
                else:
                    error_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                    print(f"Error fetching items: {response.status_code}")
                    print(f"Error details: {error_text}")
                    break
            
            print("==== ITEM RETRIEVAL SUMMARY ====")
            print(f"Successfully retrieved {len(items)} items in {batch_count} batches")
            
            # Log a few item names for verification
            if items:
                print("Sample of retrieved items:")
                for i, item in enumerate(items[:5]):
                    print(f"  {i+1}. {item.get('Name', 'Unknown')}")
                print("  ...")
            
            return items
        except Exception as e:
            print(f"Exception in get_all_items: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
            
    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """Fetch the complete list of accounts from QBO.
        
        Returns:
            List of all account data dictionaries
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO - Missing access_token or realm_id")
            return []
        
        try:
            print("==== STARTING ACCOUNT RETRIEVAL FROM QUICKBOOKS ====")
            
            accounts = []
            start_position = 1
            max_results = 1000  # QBO API limit per query
            batch_count = 0
            
            while True:
                batch_count += 1
                # Query for a batch of accounts
                query = f"SELECT * FROM Account STARTPOSITION {start_position} MAXRESULTS {max_results}"
                encoded_query = quote(query)
                url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                
                print(f"Batch {batch_count}: Requesting accounts at position {start_position}")
                
                response = requests.get(url, headers=self._get_auth_headers())
                
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    batch = data['QueryResponse'].get('Account', [])
                    
                    # If no more accounts, break the loop
                    if not batch:
                        print(f"Batch {batch_count}: No more accounts found")
                        break
                    
                    # Add this batch to our collection
                    accounts.extend(batch)
                    print(f"Batch {batch_count}: Retrieved {len(batch)} accounts (running total: {len(accounts)})")
                    
                    # If we got fewer accounts than the max, we're done
                    if len(batch) < max_results:
                        print(f"Batch {batch_count}: Less than max results, finished retrieving")
                        break
                        
                    # Otherwise, update the start position for the next batch
                    start_position += max_results
                else:
                    error_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                    print(f"Error fetching accounts: {response.status_code}")
                    print(f"Error details: {error_text}")
                    break
            
            print("==== ACCOUNT RETRIEVAL SUMMARY ====")
            print(f"Successfully retrieved {len(accounts)} accounts in {batch_count} batches")
            
            # Sort accounts by name for easier selection in the UI
            accounts.sort(key=lambda x: x.get('Name', '').lower())
            
            return accounts
        except Exception as e:
            print(f"Exception in get_all_accounts: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
            
    def get_all_payment_methods(self) -> List[Dict[str, Any]]:
        """Fetch the complete list of payment methods from QBO.
        
        Returns:
            List of all payment method data dictionaries
        """
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO - Missing access_token or realm_id")
            return []
        
        try:
            print("==== STARTING PAYMENT METHOD RETRIEVAL FROM QUICKBOOKS ====")
            
            payment_methods = []
            # Query for payment methods (there's usually not many, so no pagination needed)
            query = "SELECT * FROM PaymentMethod"
            encoded_query = quote(query)
            url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
            
            print(f"Requesting payment methods")
            
            response = requests.get(url, headers=self._get_auth_headers())
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                payment_methods = data['QueryResponse'].get('PaymentMethod', [])
                print(f"Retrieved {len(payment_methods)} payment methods")
            else:
                error_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                print(f"Error fetching payment methods: {response.status_code}")
                print(f"Error details: {error_text}")
            
            # Sort payment methods by name for easier selection in the UI
            payment_methods.sort(key=lambda x: x.get('Name', '').lower())
            
            return payment_methods
        except Exception as e:
            print(f"Exception in get_all_payment_methods: {str(e)}")
            import traceback
            traceback.print_exc()
            return []