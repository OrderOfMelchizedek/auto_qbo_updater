#!/bin/bash
# Script to run tests with proper environment setup

echo "Running FOM to QBO Automation Tests"
echo "===================================="

# Set test environment variables
export FLASK_ENV=testing
export FLASK_SECRET_KEY=test-secret-key
export GEMINI_API_KEY=test-gemini-key
export QBO_CLIENT_ID=test-client-id
export QBO_CLIENT_SECRET=test-client-secret
export QBO_REDIRECT_URI=http://localhost/callback

# Ensure we're in the project root
cd "$(dirname "$0")"

# Run tests with coverage
echo "Running pytest with coverage..."
python -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo "Coverage report available in htmlcov/index.html"
else
    echo ""
    echo "❌ Some tests failed. Please check the output above."
    exit 1
fi