import os
import json
from typing import Dict, Any, Optional, List
import time
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes

class QBOOAuthService:
    """Service for OAuth authentication with QuickBooks Online using the official Intuit library."""
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, environment: str = 'sandbox'):
        """Initialize the QBO OAuth service with credentials.
        
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
        
        # Initialize Intuit OAuth client
        self.auth_client = AuthClient(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            environment=environment
        )
        
        # API base URL
        if environment == 'sandbox':
            self.api_base = 'https://sandbox-quickbooks.api.intuit.com/v3/company/'
        else:
            self.api_base = 'https://quickbooks.api.intuit.com/v3/company/'
        
        # Realm ID (company ID)
        self.realm_id = None
    
    def get_authorization_url(self) -> str:
        """Get the QBO authorization URL for OAuth flow.
        
        Returns:
            Authorization URL to redirect the user to
        """
        # Define the scopes needed
        scopes = [
            Scopes.ACCOUNTING,
            Scopes.OPENID,
            Scopes.EMAIL
        ]
        
        # Generate the authorization URL
        auth_url = self.auth_client.get_authorization_url(scopes)
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
            # Get tokens from Intuit
            self.auth_client.get_bearer_token(authorization_code, realm_id=realm_id)
            self.realm_id = realm_id
            return True
        except Exception as e:
            print(f"Error getting tokens: {str(e)}")
            return False
    
    def refresh_tokens(self) -> bool:
        """Refresh the access token using the refresh token.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if refresh token is available
            if not self.auth_client.refresh_token:
                print("No refresh token available")
                return False
            
            # Refresh the tokens
            self.auth_client.refresh()
            return True
        except Exception as e:
            print(f"Error refreshing tokens: {str(e)}")
            return False
    
    def is_token_valid(self) -> bool:
        """Check if the current access token is valid.
        
        Returns:
            True if token is valid, False otherwise
        """
        # Simple check if access token exists
        return bool(self.auth_client.access_token)
    
    def get_auth_header(self) -> Dict[str, str]:
        """Get the authorization header for API requests.
        
        Returns:
            Dictionary with the Authorization header
        """
        return {
            'Authorization': f'Bearer {self.auth_client.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }