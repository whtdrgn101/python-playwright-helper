#!/bin/bash
# Helper script to install Playwright browsers

set -e

echo "Installing Playwright browsers..."

# Check if Playwright is installed
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "Error: Playwright Python package not found."
    echo "Please install the package first:"
    echo "  uv pip install -e ."
    echo "  or"
    echo "  pip install -e ."
    exit 1
fi

# Try to install browsers
echo "Installing Chromium (sufficient for API testing)..."
python3 -m playwright install chromium

echo ""
echo "✓ Playwright browsers installed successfully!"
echo ""
echo "To install all browsers (not needed for API testing):"
echo "  python3 -m playwright install"
echo ""
echo "To verify installation:"
echo "  python3 -c \"from playwright.sync_api import sync_playwright; print('OK')\""

