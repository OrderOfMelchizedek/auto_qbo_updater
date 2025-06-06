# QuickBooks OAuth2 Setup Guide

This guide walks you through setting up QuickBooks OAuth2 authentication for both local development and production environments.

## Prerequisites

1. QuickBooks Developer Account
2. QuickBooks App created in the developer portal
3. Python environment with required dependencies installed

## Step 1: Create QuickBooks App

1. Sign in to [QuickBooks Developer Portal](https://developer.intuit.com)
2. Create a new app or use existing one
3. Select the "QuickBooks Online Accounting" scope
4. Note down your app credentials:
   - Client ID
   - Client Secret

## Step 2: Configure Redirect URIs

### For Local Development

Add these redirect URIs in your QuickBooks app settings:

```
http://localhost:5000/api/auth/qbo/callback
http://localhost:3000/auth/callback
```

### For Production (Heroku)

Add your production redirect URI:

```
https://your-app-name.herokuapp.com/api/auth/qbo/callback
```

## Step 3: Set Environment Variables

### Local Development

Create a `.env` file in the project root:

```bash
# QuickBooks OAuth2
QBO_CLIENT_ID="your_client_id_here"
QBO_CLIENT_SECRET="your_client_secret_here"
QBO_REDIRECT_URI="http://localhost:5000/api/auth/qbo/callback"
QBO_ENVIRONMENT="sandbox"  # Use "production" for live apps

# Generate encryption key
ENCRYPTION_KEY="generate_with_command_below"
```

Generate encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Production (Heroku)

Set environment variables on Heroku:

```bash
heroku config:set QBO_CLIENT_ID="your_client_id_here"
heroku config:set QBO_CLIENT_SECRET="your_client_secret_here"
heroku config:set QBO_REDIRECT_URI="https://your-app.herokuapp.com/api/auth/qbo/callback"
heroku config:set QBO_ENVIRONMENT="production"
heroku config:set ENCRYPTION_KEY="your_generated_key"
```

## Step 4: Test OAuth2 Implementation

### Run the test script:

```bash
python scripts/test_oauth2.py
```

This will verify your configuration is correct.

### Test the flow manually:

1. Start the Flask backend:
   ```bash
   python -m src.app
   ```

2. Get authorization URL:
   ```bash
   curl http://localhost:5000/api/auth/qbo/authorize \
     -H "X-Session-ID: test-session-123"
   ```

3. Visit the returned `auth_url` in your browser
4. Authenticate with QuickBooks
5. You'll be redirected to your callback URL with authorization code

## Step 5: Handle OAuth2 in Frontend

The frontend needs to:

1. Open authorization URL in popup window
2. Listen for callback completion
3. Store session ID for subsequent API calls
4. Check authentication status periodically

Example flow:

```javascript
// 1. Get authorization URL
const response = await fetch('/api/auth/qbo/authorize', {
  headers: {
    'X-Session-ID': sessionId
  }
});
const { auth_url } = await response.json();

// 2. Open popup
const authWindow = window.open(auth_url, 'qbo-auth', 'width=600,height=700');

// 3. Listen for callback (implement in callback page)
window.addEventListener('message', (event) => {
  if (event.data.type === 'qbo-auth-complete') {
    authWindow.close();
    // Check auth status
  }
});
```

## API Endpoints

### Get Authorization URL
```
GET /api/auth/qbo/authorize
Headers: X-Session-ID
Response: { auth_url, state, session_id }
```

### Handle Callback
```
GET /api/auth/qbo/callback?code=xxx&state=xxx&realmId=xxx
Headers: X-Session-ID
Response: { success, realm_id, expires_at }
```

### Check Status
```
GET /api/auth/qbo/status
Headers: X-Session-ID
Response: { authenticated, realm_id, token_valid, expires_at }
```

### Refresh Token
```
POST /api/auth/qbo/refresh
Headers: X-Session-ID
Response: { success, expires_at }
```

### Revoke Access
```
POST /api/auth/qbo/revoke
Headers: X-Session-ID
Response: { success, message }
```

## Security Notes

1. **Session Management**: The implementation uses session IDs to track OAuth2 state and tokens. Store the session ID securely in your frontend.

2. **Token Encryption**: All tokens are encrypted before storage using Fernet symmetric encryption.

3. **CSRF Protection**: State parameter is validated during callback to prevent CSRF attacks.

4. **Token Expiry**: Access tokens expire after 1 hour, refresh tokens after 100 days.

## Troubleshooting

### Common Issues

1. **"Invalid state parameter"**
   - Ensure you're using the same session ID throughout the flow
   - Check that state hasn't expired (10 minute TTL)

2. **"No valid refresh token found"**
   - User needs to re-authenticate
   - Check if 100 days have passed since last auth

3. **CORS errors**
   - Ensure Flask CORS is properly configured
   - Check redirect URI matches exactly

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

After OAuth2 is working:

1. Implement QuickBooks API client
2. Add customer search/matching
3. Create sales receipts
4. Handle webhooks for real-time updates
