import os
import json
import requests
from typing import Dict, Any, Optional, List
import base64
from urllib.parse import urlencode, quote
import time
import random
import string

from flask import session as flask_session

class QBOService:
    def __init__(self, client_id, client_secret, redirect_uri, environment='sandbox'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.environment = environment

        if self.environment == 'sandbox':
            self.api_base = 'https://sandbox-quickbooks.api.intuit.com/v3/company/'
            # Define OAuth endpoints for sandbox
            self.authorization_endpoint = 'https://sandbox-appcenter.intuit.com/connect/oauth2'
            self.token_endpoint = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'
        else:
            self.api_base = 'https://quickbooks.api.intuit.com/v3/company/'
            # Define OAuth endpoints for production
            self.authorization_endpoint = 'https://appcenter.intuit.com/connect/oauth2'
            self.token_endpoint = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'

        # Instance variables for tokens
        self.access_token = None
        self.refresh_token = None
        self.realm_id = None # This will be set after successful token exchange
        self.token_expires_at = 0 # Unix timestamp for when the access token expires

    def get_authorization_url(self) -> str:
        """
        Constructs the QuickBooks Online authorization URL.
        """
        scopes = [
            'com.intuit.quickbooks.accounting',
            'openid',
            'profile',
            'email',
        ]
        scope_string = ' '.join(scopes)

        state_token = ''.join(random.choices(string.ascii_letters + string.digits, k=30))
        if hasattr(flask_session, 'get'): # Check if in Flask request context
            flask_session['qbo_oauth_state'] = state_token
            flask_session.modified = True


        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': scope_string,
            'redirect_uri': self.redirect_uri,
            'state': state_token
        }
        return f"{self.authorization_endpoint}?{urlencode(params)}"

    def _ensure_tokens_loaded(self):
        """Loads tokens from session if not present on instance for current context."""
        if not self.access_token and hasattr(flask_session, 'get'):
            self.access_token = flask_session.get('qbo_access_token')
            self.refresh_token = flask_session.get('qbo_refresh_token')
            self.realm_id = flask_session.get('qbo_realm_id')
            self.token_expires_at = flask_session.get('qbo_token_expires_at', 0)
            if self.access_token:
                print("DEBUG: QBOService loaded tokens from session.")

    def _save_tokens_to_session(self):
        """Saves current instance tokens to flask session."""
        if hasattr(flask_session, 'get'):
            flask_session['qbo_access_token'] = self.access_token
            flask_session['qbo_refresh_token'] = self.refresh_token
            flask_session['qbo_realm_id'] = self.realm_id
            flask_session['qbo_token_expires_at'] = self.token_expires_at
            flask_session.modified = True
            print("DEBUG: QBOService saved tokens to session.")

    def get_tokens(self, authorization_code: str, realm_id: str) -> bool:
        """
        Exchanges an authorization code for access and refresh tokens.
        Saves tokens to the session.
        """
        payload = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.redirect_uri
        }
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode('utf-8')).decode('utf-8')
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        try:
            response = requests.post(self.token_endpoint, data=payload, headers=headers)
            response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
            token_data = response.json()

            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            self.realm_id = realm_id # Crucial: set realm_id from callback
            self.token_expires_at = int(time.time()) + token_data.get('expires_in', 3600)
            
            self._save_tokens_to_session()
            print(f"DEBUG: Tokens obtained and saved. Realm ID: {self.realm_id}")
            return True
        except requests.exceptions.RequestException as e:
            error_content = e.response.text if e.response else "No response content"
            print(f"Error getting tokens: {e}. Status: {e.response.status_code if e.response else 'N/A'}. Content: {error_content}")
            self.access_token = None
            self.refresh_token = None
            # Do not clear realm_id here as it came from the auth redirect
            self._save_tokens_to_session() # Save cleared token state
            return False
        except Exception as e: # Catch any other unexpected error
            print(f"Unexpected error in get_tokens: {str(e)}")
            self.access_token = None
            self.refresh_token = None
            self._save_tokens_to_session()
            return False


    def refresh_access_token(self) -> bool:
        """
        Refreshes the access token using the stored refresh token.
        Saves new tokens to the session.
        """
        self._ensure_tokens_loaded()
        if not self.refresh_token:
            print("No refresh token available to refresh.")
            return False

        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode('utf-8')).decode('utf-8')
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        try:
            response = requests.post(self.token_endpoint, data=payload, headers=headers)
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token', self.refresh_token) # QBO often returns new refresh token
            self.token_expires_at = int(time.time()) + token_data.get('expires_in', 3600)
            
            self._save_tokens_to_session()
            print("DEBUG: Access token refreshed and saved.")
            return True
        except requests.exceptions.RequestException as e:
            error_content = e.response.text if e.response else "No response content"
            print(f"Error refreshing token: {e}. Status: {e.response.status_code if e.response else 'N/A'}. Content: {error_content}")
            # If refresh fails (e.g. invalid_grant), tokens might be totally invalid
            if e.response is not None and e.response.status_code in [400, 401, 403]:
                print("Clearing tokens due to refresh failure.")
                self.access_token = None
                self.refresh_token = None
                self.realm_id = None # If tokens are bad, realm association might be stale too
                self.token_expires_at = 0
                self._save_tokens_to_session()
            return False
        except Exception as e:
            print(f"Unexpected error in refresh_access_token: {str(e)}")
            return False

    def _get_auth_headers(self) -> Dict[str, str]:
        self._ensure_tokens_loaded()
        if not self.access_token or not self.realm_id:
            raise Exception("QBOService: Not authenticated. Cannot get auth headers.")
        
        current_time = int(time.time())
        if current_time >= (self.token_expires_at - 60): # Refresh if token is expired or will expire in 60s
            print("Access token expired or expiring soon, attempting refresh...")
            if not self.refresh_access_token():
                raise Exception("QBOService: Token refresh failed. Cannot get auth headers.")
        
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
        self._ensure_tokens_loaded() 
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return None
        
        if not customer_lookup or customer_lookup.strip() == '':
            print("Empty customer lookup value")
            return None
            
        safe_lookup = customer_lookup.replace("'", "''")
        
        try:
            print(f"Finding customer with progressive matching: '{customer_lookup}'")
            
            # Strategy 1: Exact match on DisplayName
            query = f"SELECT * FROM Customer WHERE DisplayName = '{safe_lookup}'"
            encoded_query = quote(query)
            url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
            
            response = requests.get(url, headers=self._get_auth_headers())
            
            if response.status_code == 200:
                data = response.json()
                if data['QueryResponse'].get('Customer'):
                    print(f"Strategy 1 - Exact match found: {data['QueryResponse']['Customer'][0].get('DisplayName')}")
                    return data['QueryResponse']['Customer'][0]
            else:
                print(f"QBO API Error (Strategy 1): {response.status_code} - {response.text}")

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
            else:
                print(f"QBO API Error (Strategy 2): {response.status_code} - {response.text}")
            
            # Strategy 3: Reversed name parts
            name_parts = safe_lookup.split()
            if len(name_parts) >= 2:
                if ',' not in safe_lookup:
                    reversed_name = f"{name_parts[-1]}, {' '.join(name_parts[:-1])}"
                    query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{reversed_name}%'"
                    encoded_query = quote(query)
                    url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                    response = requests.get(url, headers=self._get_auth_headers())
                    if response.status_code == 200:
                        data = response.json()
                        if data['QueryResponse'].get('Customer'):
                            print(f"Strategy 3a - Reversed name match: {data['QueryResponse']['Customer'][0].get('DisplayName')}")
                            return data['QueryResponse']['Customer'][0]
                    else:
                        print(f"QBO API Error (Strategy 3a): {response.status_code} - {response.text}")

                elif ',' in safe_lookup:
                    parts = safe_lookup.split(',')
                    if len(parts) == 2:
                        space_separated = f"{parts[1].strip()} {parts[0].strip()}"
                        query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{space_separated}%'"
                        encoded_query = quote(query)
                        url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                        response = requests.get(url, headers=self._get_auth_headers())
                        if response.status_code == 200:
                            data = response.json()
                            if data['QueryResponse'].get('Customer'):
                                print(f"Strategy 3b - Comma to space conversion match: {data['QueryResponse']['Customer'][0].get('DisplayName')}")
                                return data['QueryResponse']['Customer'][0]
                        else:
                            print(f"QBO API Error (Strategy 3b): {response.status_code} - {response.text}")
            
            # Further strategies (4, 5, 6) can be added here, ensuring to handle potential API errors for each call.

            print(f"No matching customer found for: '{customer_lookup}' after trying all strategies")
            return None
        
        except Exception as e:
            print(f"Exception in find_customer: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def create_customer(self, customer_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self._ensure_tokens_loaded()
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return None
        
        try:
            url = f"{self.api_base}{self.realm_id}/customer"
            response = requests.post(url, headers=self._get_auth_headers(), json=customer_data)
            response.raise_for_status()
            return response.json().get('Customer')
        except requests.exceptions.RequestException as e:
            print(f"Error creating customer: {e.response.status_code if e.response else 'N/A'} - {e.response.text if e.response else str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error in create_customer: {str(e)}")
            return None

    def update_customer(self, customer_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self._ensure_tokens_loaded()
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return None
        
        try:
            url = f"{self.api_base}{self.realm_id}/customer" # QBO uses POST for updates with sparse=true or full object
            # Ensure 'sparse': True is in customer_data if doing a sparse update,
            # or provide the full object as per QBO docs for full update.
            # QBO typically requires Id and SyncToken for updates.
            response = requests.post(url, headers=self._get_auth_headers(), json=customer_data)
            response.raise_for_status()
            return response.json().get('Customer')
        except requests.exceptions.RequestException as e:
            print(f"Error updating customer: {e.response.status_code if e.response else 'N/A'} - {e.response.text if e.response else str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error in update_customer: {str(e)}")
            return None

    def create_sales_receipt(self, sales_receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_tokens_loaded()
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO")
            return {"error": True, "message": "Not authenticated with QBO"}
        
        try:
            url = f"{self.api_base}{self.realm_id}/salesreceipt"
            response = requests.post(url, headers=self._get_auth_headers(), json=sales_receipt_data)
            
            if response.status_code == 200:
                return response.json().get('SalesReceipt', {"error": True, "message": "SalesReceipt key missing in successful response"})
            else:
                error_data = {"error": True, "message": f"Error creating sales receipt: {response.status_code}"}
                try:
                    error_json = response.json()
                    error_data['detail'] = error_json.get('Fault', {}).get('Error', [{}])[0].get('Detail', response.text)
                    error_data['qbo_message'] = error_json.get('Fault', {}).get('Error', [{}])[0].get('Message', '')
                    error_data['code'] = error_json.get('Fault', {}).get('Error', [{}])[0].get('code', '')
                    # ... (rest of your detailed error parsing logic from original file) ...
                except json.JSONDecodeError:
                    error_data['detail'] = response.text
                print(f"Error creating sales receipt: {error_data}")
                return error_data
        
        except requests.exceptions.RequestException as e:
            message = str(e)
            if e.response is not None:
                message = f"{e.response.status_code} - {e.response.text}"
            print(f"RequestException in create_sales_receipt: {message}")
            return {"error": True, "message": f"RequestException: {message}"}
        except Exception as e:
            print(f"Unexpected error in create_sales_receipt: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": True, "message": str(e)}

    def get_all_customers(self) -> List[Dict[str, Any]]:
        self._ensure_tokens_loaded()
        if not self.access_token or not self.realm_id:
            print("Not authenticated with QBO for get_all_customers")
            return []
        
        customers = []
        start_position = 1
        max_results = 1000 
        
        try:
            while True:
                query = f"SELECT * FROM Customer STARTPOSITION {start_position} MAXRESULTS {max_results}"
                encoded_query = quote(query)
                url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                response = requests.get(url, headers=self._get_auth_headers())
                response.raise_for_status()
                
                data = response.json()
                batch = data.get('QueryResponse', {}).get('Customer', [])
                if not batch:
                    break
                customers.extend(batch)
                if len(batch) < max_results:
                    break
                start_position += len(batch) # More robust than max_results
            return customers
        except requests.exceptions.RequestException as e:
            print(f"Error fetching all customers: {e.response.status_code if e.response else 'N/A'} - {e.response.text if e.response else str(e)}")
            return []
        except Exception as e:
            print(f"Unexpected error in get_all_customers: {str(e)}")
            return []

    # Generic method to get all of a certain entity type
    def _get_all_entities(self, entity_name: str) -> List[Dict[str, Any]]:
        self._ensure_tokens_loaded()
        if not self.access_token or not self.realm_id:
            print(f"Not authenticated with QBO for get_all_{entity_name.lower()}s")
            return []

        entities = []
        start_position = 1
        max_results = 1000 # QBO API limit per query

        try:
            print(f"==== STARTING {entity_name.upper()} RETRIEVAL FROM QUICKBOOKS ====")
            while True:
                query = f"SELECT * FROM {entity_name} STARTPOSITION {start_position} MAXRESULTS {max_results}"
                encoded_query = quote(query)
                url = f"{self.api_base}{self.realm_id}/query?query={encoded_query}"
                print(f"Requesting {entity_name}s at position {start_position}")
                
                response = requests.get(url, headers=self._get_auth_headers())
                response.raise_for_status() # Check for HTTP errors

                data = response.json()
                batch = data.get('QueryResponse', {}).get(entity_name, [])
                
                if not batch:
                    print(f"No more {entity_name}s found.")
                    break
                
                entities.extend(batch)
                print(f"Retrieved {len(batch)} {entity_name}s (running total: {len(entities)})")

                if len(batch) < max_results:
                    print(f"Less than max results, finished retrieving {entity_name}s.")
                    break
                
                start_position += len(batch) 
            
            print(f"==== {entity_name.upper()} RETRIEVAL SUMMARY ====")
            print(f"Successfully retrieved {len(entities)} {entity_name.lower()}s.")
            if entities:
                entities.sort(key=lambda x: x.get('Name', '').lower()) # Sort if Name exists
            return entities

        except requests.exceptions.RequestException as e:
            error_text = e.response.text if e.response else str(e)
            status_code = e.response.status_code if e.response else "N/A"
            print(f"Error fetching all {entity_name.lower()}s: {status_code} - {error_text}")
            return []
        except Exception as e:
            print(f"Unexpected error in _get_all_entities for {entity_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def get_all_items(self) -> List[Dict[str, Any]]:
        return self._get_all_entities("Item")

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        return self._get_all_entities("Account")

    def get_all_payment_methods(self) -> List[Dict[str, Any]]:
        return self._get_all_entities("PaymentMethod")

    # Generic method to create an entity
    def _create_entity(self, entity_name: str, entity_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self._ensure_tokens_loaded()
        if not self.access_token or not self.realm_id:
            print(f"Not authenticated with QBO for create_{entity_name.lower()}")
            return None
        
        if 'Name' not in entity_data: # Basic validation
            print(f"Missing required 'Name' field for {entity_name} creation.")
            return None

        try:
            url = f"{self.api_base}{self.realm_id}/{entity_name.lower()}"
            response = requests.post(url, headers=self._get_auth_headers(), json=entity_data)
            response.raise_for_status()
            
            created_entity = response.json().get(entity_name)
            if created_entity:
                print(f"Successfully created {entity_name}: {created_entity.get('Name')} (ID: {created_entity.get('Id')})")
            return created_entity
        except requests.exceptions.RequestException as e:
            error_text = e.response.text if e.response else str(e)
            status_code = e.response.status_code if e.response else "N/A"
            print(f"Error creating {entity_name}: {status_code} - {error_text}")
            return None
        except Exception as e:
            print(f"Unexpected error in _create_entity for {entity_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def create_account(self, account_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if 'AccountType' not in account_data: # Account specific validation
            print("Missing required 'AccountType' field for account creation.")
            return None
        return self._create_entity("Account", account_data)

    def create_item(self, item_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if 'Type' not in item_data: # Item specific validation
            print("Missing required 'Type' field for item creation.")
            return None
        # Default IncomeAccountRef if not provided (example, adjust as needed)
        if 'IncomeAccountRef' not in item_data:
             print("Warning: 'IncomeAccountRef' not provided for item creation. QBO might use a default or error.")
        return self._create_entity("Item", item_data)

    def create_payment_method(self, payment_method_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self._create_entity("PaymentMethod", payment_method_data)