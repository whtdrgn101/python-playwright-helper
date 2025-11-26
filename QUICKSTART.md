# Quick Start Guide

## Installation

### Prerequisites

- Python 3.9 or higher
- UV package manager

### Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install the Package

```bash
# From source
cd python-rest-api-testing
uv pip install -e .

# Or from ProGet (after publishing)
uv pip install rest-api-testing
```

### Install Playwright Browsers

**Important:** After installing the package, you must install Playwright browsers:

```bash
# Use Python module (recommended)
python3 -m playwright install

# Or if playwright command is available
playwright install

# For API testing only, install just Chromium (saves space)
python3 -m playwright install chromium
```

**Troubleshooting:** If `playwright install` fails, see `INSTALL.md` for detailed solutions.

## Configuration

1. Copy the example properties file:
   ```bash
   cp application.properties.example application.properties
   ```

2. Edit `application.properties` with your settings:
   ```properties
   ping.federate.base.url=https://your-ping-federate-server.com
   ping.federate.token.endpoint=/as/token.oauth2
   ping.federate.client.id=${PING_CLIENT_ID}
   ping.federate.client.secret=${PING_CLIENT_SECRET}
   api.base.url=https://your-api-server.com/api
   ```

3. Set environment variables:
   ```bash
   export PING_CLIENT_ID=your-client-id
   export PING_CLIENT_SECRET=your-client-secret
   ```

## Writing Your First Test

Create a test file `tests/test_my_api.py`:

```python
import pytest
from rest_api_testing import BaseApiTest


class TestMyAPI(BaseApiTest):
    """My API test class."""
    
    def test_get_users(self):
        """Test getting users."""
        response = self.authenticated_request.get("/users")
        
        response.should_have.status_code(200)
        response.should_have.json_path("users", exists=True)
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_my_api.py

# Run with verbose output
pytest -v

# Run with output
pytest -s
```

## Next Steps

- See `EXAMPLES.md` for comprehensive validation examples
- See `README.md` for full documentation
- Check `tests/example_test.py` for more examples

