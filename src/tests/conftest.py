"""Pytest configuration file for test fixtures and settings."""
import os

# Set DEBUG to true for tests to disable TrustedHostMiddleware
# which causes issues with test client not having proper host headers
os.environ["DEBUG"] = "true"

# Ensure other necessary test environment variables are set
if "JWT_SECRET_KEY" not in os.environ:
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"

if "QBO_CLIENT_ID" not in os.environ:
    os.environ["QBO_CLIENT_ID"] = "test-client-id"

if "QBO_CLIENT_SECRET" not in os.environ:
    os.environ["QBO_CLIENT_SECRET"] = "test-client-secret"

if "QBO_REDIRECT_URI" not in os.environ:
    os.environ["QBO_REDIRECT_URI"] = "http://localhost:8000/api/auth/callback"

if "QBO_ENVIRONMENT" not in os.environ:
    os.environ["QBO_ENVIRONMENT"] = "sandbox"
