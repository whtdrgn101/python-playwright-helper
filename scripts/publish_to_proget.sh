#!/bin/bash
# Script to build and publish the Python package to ProGet

set -e

# Configuration
PACKAGE_NAME="rest-api-testing"
VERSION=$(python -c "import tomli; print(tomli.load(open('pyproject.toml'))['project']['version'])")
PROGET_URL="${PROGET_URL:-https://your-proget-server.com}"
PROGET_FEED="${PROGET_FEED:-python-packages}"
PROGET_API_KEY="${PROGET_API_KEY}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building Python package...${NC}"

# Build the package
uv build

# Get the built wheel file
WHEEL_FILE=$(ls -t dist/*.whl | head -1)

if [ -z "$WHEEL_FILE" ]; then
    echo -e "${RED}Error: No wheel file found in dist/ directory${NC}"
    exit 1
fi

echo -e "${GREEN}Built package: ${WHEEL_FILE}${NC}"

# Check if ProGet API key is set
if [ -z "$PROGET_API_KEY" ]; then
    echo -e "${YELLOW}Warning: PROGET_API_KEY not set. Skipping upload.${NC}"
    echo -e "${YELLOW}To upload, set PROGET_API_KEY environment variable and run:${NC}"
    echo -e "${YELLOW}  curl -X PUT \"${PROGET_URL}/api/packages/${PROGET_FEED}/upload\" \\${NC}"
    echo -e "${YELLOW}    -H \"X-ApiKey: \$PROGET_API_KEY\" \\${NC}"
    echo -e "${YELLOW}    -F \"file=@${WHEEL_FILE}\"${NC}"
    exit 0
fi

# Upload to ProGet
echo -e "${GREEN}Uploading to ProGet...${NC}"

UPLOAD_URL="${PROGET_URL}/api/packages/${PROGET_FEED}/upload"

RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "$UPLOAD_URL" \
    -H "X-ApiKey: $PROGET_API_KEY" \
    -F "file=@$WHEEL_FILE")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    echo -e "${GREEN}Successfully uploaded ${PACKAGE_NAME} v${VERSION} to ProGet${NC}"
    echo -e "${GREEN}Package available at: ${PROGET_URL}/packages/${PROGET_FEED}/${PACKAGE_NAME}${NC}"
else
    echo -e "${RED}Error uploading to ProGet. HTTP Status: ${HTTP_CODE}${NC}"
    echo -e "${RED}Response: ${BODY}${NC}"
    exit 1
fi

