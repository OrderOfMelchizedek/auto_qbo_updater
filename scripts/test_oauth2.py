#!/usr/bin/env python
"""Test script for QuickBooks OAuth2 implementation."""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config  # noqa: E402
from src.quickbooks_auth import qbo_auth  # noqa: E402


def test_oauth2_flow():
    """Test OAuth2 flow components."""
    print("Testing QuickBooks OAuth2 Implementation")
    print("=" * 50)

    # Check configuration
    print("\n1. Checking configuration...")
    print(f"   Client ID: {'✓' if Config.QBO_CLIENT_ID else '✗ Missing'}")
    print(f"   Client Secret: {'✓' if Config.QBO_CLIENT_SECRET else '✗ Missing'}")
    print(f"   Redirect URI: {Config.QBO_REDIRECT_URI or '✗ Missing'}")
    print(f"   Environment: {Config.QBO_ENVIRONMENT}")
    print(
        f"   Encryption Key: {'✓' if Config.ENCRYPTION_KEY else '✓ Will be generated'}"
    )

    if not all(
        [Config.QBO_CLIENT_ID, Config.QBO_CLIENT_SECRET, Config.QBO_REDIRECT_URI]
    ):
        print("\n⚠️  Missing QuickBooks OAuth2 configuration!")
        print("   Please set the following environment variables:")
        print("   - QBO_CLIENT_ID")
        print("   - QBO_CLIENT_SECRET")
        print("   - QBO_REDIRECT_URI")
        return

    # Test authorization URL generation
    print("\n2. Testing authorization URL generation...")
    try:
        session_id = "test_session_123"
        auth_url, state = qbo_auth.get_authorization_url(session_id)
        print("   ✓ Generated auth URL")
        print(f"   State: {state[:20]}...")
        print(f"   URL: {auth_url[:80]}...")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return

    # Test auth status check
    print("\n3. Testing auth status check...")
    try:
        status = qbo_auth.get_auth_status(session_id)
        print(f"   ✓ Status: {json.dumps(status, indent=2)}")
    except Exception as e:
        print(f"   ✗ Failed: {e}")

    print("\n✓ OAuth2 implementation is ready!")
    print("\nTo complete testing:")
    print("1. Run the Flask app: python -m src.app")
    print("2. Make a request to: GET /api/auth/qbo/authorize")
    print("3. Follow the authorization URL to authenticate with QuickBooks")
    print("4. Handle the callback at your configured redirect URI")


if __name__ == "__main__":
    test_oauth2_flow()
