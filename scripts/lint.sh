#!/bin/bash
# Run all linting tools locally before pushing to CI

set -e  # Exit on error

echo "🔍 Running local linting checks..."
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Run flake8
echo "1️⃣  Running flake8..."
if flake8 src tests; then
    echo "✅ flake8 passed!"
else
    echo "❌ flake8 failed!"
    exit 1
fi
echo ""

# Run black
echo "2️⃣  Running black..."
if black --check src tests; then
    echo "✅ black passed!"
else
    echo "❌ black failed! Run 'black src tests' to fix."
    exit 1
fi
echo ""

# Run isort
echo "3️⃣  Running isort..."
if isort --check-only src tests; then
    echo "✅ isort passed!"
else
    echo "❌ isort failed! Run 'isort src tests' to fix."
    exit 1
fi
echo ""

# Run bandit (optional - security check)
echo "4️⃣  Running bandit security scan..."
if command -v bandit &> /dev/null; then
    bandit -r src --severity-level high -f json | jq -e '.results | length == 0' > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ No high severity security issues!"
    else
        echo "⚠️  High severity security issues found! Run 'bandit -r src' for details."
        exit 1
    fi
else
    echo "⏭️  bandit not installed, skipping security scan"
fi
echo ""

echo "🎉 All linting checks passed! Ready to push."