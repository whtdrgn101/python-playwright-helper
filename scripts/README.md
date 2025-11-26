# Deployment Scripts

## Publishing to ProGet

### Prerequisites

1. Set environment variables:
   ```bash
   export PROGET_URL=https://your-proget-server.com
   export PROGET_FEED=python-packages  # Optional, defaults to python-packages
   export PROGET_API_KEY=your-api-key
   ```

2. Make the script executable:
   ```bash
   chmod +x scripts/publish_to_proget.sh
   ```

### Usage

```bash
# Build and publish to ProGet
./scripts/publish_to_proget.sh
```

### Manual Upload

If you prefer to upload manually:

```bash
# Build the package
uv build

# Upload using curl
curl -X PUT "https://your-proget-server.com/api/packages/python-packages/upload" \
  -H "X-ApiKey: your-api-key" \
  -F "file=@dist/rest_api_testing-1.0.0-py3-none-any.whl"
```

### Installing from ProGet

Once published, users can install the package from ProGet:

```bash
# Configure pip to use ProGet
pip config set global.index-url https://your-proget-server.com/nuget/python-packages/simple

# Install the package
pip install rest-api-testing
```

Or using UV:

```bash
# Configure UV to use ProGet
export UV_INDEX_URL=https://your-proget-server.com/nuget/python-packages/simple

# Install the package
uv pip install rest-api-testing
```

