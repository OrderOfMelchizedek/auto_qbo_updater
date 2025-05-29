#!/bin/bash
# Automatically fix formatting issues

echo "🔧 Auto-formatting code..."
echo ""

# Change to project root
cd "$(dirname "$0")/.."

# Run isort
echo "1️⃣  Running isort..."
isort src tests
echo "✅ Import sorting complete!"
echo ""

# Run black
echo "2️⃣  Running black..."
black src tests
echo "✅ Code formatting complete!"
echo ""

# Run flake8 to check remaining issues
echo "3️⃣  Checking for remaining issues with flake8..."
if flake8 src tests; then
    echo "✅ No remaining issues!"
else
    echo "⚠️  Some issues remain that need manual fixing:"
    flake8 src tests
fi
echo ""

echo "🎉 Formatting complete! Run './scripts/lint.sh' to verify all checks pass."
