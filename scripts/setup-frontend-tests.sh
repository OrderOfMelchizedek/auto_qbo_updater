#!/bin/bash

# Setup script for frontend JavaScript tests
# This script installs the necessary dependencies for frontend testing

set -e  # Exit on error

echo "🔧 Setting up frontend testing environment..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ and npm 8+"
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node --version | cut -d'v' -f2)
NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)

if [ "$NODE_MAJOR" -lt 16 ]; then
    echo "❌ Node.js version $NODE_VERSION is too old. Please install Node.js 16 or higher."
    exit 1
fi

echo "✅ Node.js version: $(node --version)"
echo "✅ npm version: $(npm --version)"

# Install root-level dependencies (ESLint)
echo "📦 Installing root-level dependencies..."
npm install

# Install frontend test dependencies
echo "📦 Installing frontend test dependencies..."
cd tests/frontend
npm install

echo ""
echo "🎉 Frontend testing environment setup complete!"
echo ""
echo "Available commands:"
echo "  npm run lint:js              - Lint JavaScript files"
echo "  npm run lint:js:fix          - Lint and fix JavaScript files"
echo "  npm run test:frontend        - Run frontend tests"
echo "  npm run test:frontend:coverage - Run frontend tests with coverage"
echo "  npm run test:frontend:watch  - Run frontend tests in watch mode"
echo ""
echo "To run tests directly:"
echo "  cd tests/frontend && npm test"
echo ""
echo "Pre-commit hooks will now include frontend tests when you commit JavaScript changes."
