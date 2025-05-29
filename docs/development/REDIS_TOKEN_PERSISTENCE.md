# QuickBooks OAuth Token Persistence with Redis

## Overview
This implementation adds Redis-based token persistence to solve the issue of OAuth tokens being lost when Heroku workers restart or between different workers.

## Changes Made

### 1. QBOService (`src/utils/qbo_service.py`)
- Added `redis` import
- Modified `__init__` to accept optional `redis_client` parameter
- Changed token attributes to private with underscore prefix (`_access_token`, etc.)
- Added property getters/setters for tokens that automatically save to Redis
- Added `_save_token_to_redis()` method to persist tokens with 90-day expiration
- Added `_load_tokens_from_redis()` method to restore tokens on initialization
- Added `clear_tokens()` method to remove tokens from both memory and Redis

### 2. Flask App (`src/app.py`)
- Added Redis client initialization using the existing `REDIS_URL`
- Pass Redis client to QBOService constructor
- Added `/qbo/disconnect` endpoint to clear tokens and disconnect from QBO
- Updated callback to set proper session flags

## How It Works

1. **Token Storage**: When tokens are set via property setters, they're automatically saved to Redis with keys like:
   - `qbo_tokens:sandbox:access_token`
   - `qbo_tokens:sandbox:refresh_token`
   - `qbo_tokens:sandbox:realm_id`
   - `qbo_tokens:sandbox:token_expires_at`

2. **Token Loading**: When QBOService is initialized, it automatically loads any existing tokens from Redis.

3. **Token Expiration**: Tokens in Redis expire after 90 days (QBO refresh tokens last 100 days).

4. **Environment Separation**: Token keys include the environment (sandbox/production) to prevent mixing.

## Benefits

- Tokens persist across worker restarts
- Tokens are shared between multiple workers
- No token loss during deployments
- Automatic token loading on app startup
- Graceful fallback if Redis is unavailable

## Testing

To verify the implementation:
1. Connect to QuickBooks
2. Restart the app or wait for worker cycling
3. Check `/qbo/auth-status` - should still show authenticated
4. Test creating sales receipts - should work without re-authentication

## Monitoring

Check logs for:
- "Redis connection established for QBO token persistence"
- "Loaded QBO tokens from Redis (realm_id: XXX)"
- "Saved [token_type] to Redis"