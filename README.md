# REST API Testing Framework (Python)

A Python-based REST API testing framework using Playwright, pytest, and Jinja2. Designed for testing REST APIs with JWT authentication via PING Federate.

## Features

- **Python 3.9+** - Modern Python support
- **Playwright** - Modern API and browser testing library
- **pytest** - Modern testing framework
- **Jinja2 Templates** - Generate JSON request bodies from templates
- **CSV Data Loading** - Load test data from CSV files only
- **JWT Authentication** - Automatic token retrieval from PING Federate
- **OAuth Scope Declaration** - Declare OAuth scopes at class or method level
- **Configurable** - Environment-based configuration with .env files
- **Token Caching** - Efficient token management with caching (with Bypass option)
- **Pythonic API** - Clean, idiomatic Python patterns

## Installation

### Prerequisites

- Python 3.9 or higher
- UV package manager (optional but recommended)

### Install UV (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install the Package

**From Source:**
```bash
cd rest-api-testing-python
uv pip install -e .
```

**Or using pip:**
```bash
pip install -e .
```

### Install Playwright Browsers

After installing the package, you **must** install the Playwright browser binaries:

```bash
# Recommended method (use Python module)
python3 -m playwright install

# Or if playwright is in your PATH
playwright install

# For API testing only, you can install just Chromium (lighter)
python3 -m playwright install chromium
```

**Note:** For REST API testing, you typically only need Chromium, not all browsers. This saves disk space (~500MB vs ~1.5GB).

### Troubleshooting Playwright Installation

If `playwright install` fails, try:

1. **Use Python module instead:**
   ```bash
   python3 -m playwright install
   ```

2. **Install system dependencies (Ubuntu/Debian):**
   ```bash
   sudo apt-get update
   sudo apt-get install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
       libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libxcomposite1 \
       libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2
   ```

3. **Install with dependencies:**
   ```bash
   python3 -m playwright install --with-deps chromium
   ```

4. **Check if Playwright package is installed:**
   ```bash
   python3 -c "import playwright; print('Playwright installed')"
   ```

See `INSTALL.md` for detailed troubleshooting steps.

## Configuration

Configuration is managed through `.env` files or environment variables. The framework uses Pythonic naming conventions (snake_case) for all configuration options.

### 1. Create .env File

Create a `.env` file in your project root (you can copy from `.env.example`):

```bash
cp .env.example .env
```

### 2. Configure Your Settings

Edit the `.env` file with your configuration:

```env
# PING Federate Configuration
PING_FEDERATE_BASE_URL=https://your-ping-federate-server.com
PING_FEDERATE_TOKEN_ENDPOINT=/as/token.oauth2
PING_FEDERATE_CLIENT_ID=your-client-id
PING_FEDERATE_CLIENT_SECRET=your-client-secret
PING_FEDERATE_GRANT_TYPE=client_credentials

# API Base URL
API_BASE_URL=https://your-api-server.com/api

# Test Configuration
TEST_TIMEOUT=30000
TEST_CONNECTION_TIMEOUT=10000

# Logging Configuration
LOG_DIRECTORY=logs
LOG_LEVEL=INFO
LOG_REQUEST_BODY=true
LOG_RESPONSE_BODY=true
LOG_MASK_SENSITIVE_HEADERS=true
```

### 3. Environment Variables (Alternative)

You can also set configuration via environment variables instead of using a `.env` file:

```bash
export PING_FEDERATE_BASE_URL=https://your-ping-federate-server.com
export PING_FEDERATE_CLIENT_ID=your-client-id
export PING_FEDERATE_CLIENT_SECRET=your-client-secret
export API_BASE_URL=https://your-api-server.com/api
```

**Note:** Environment variables take precedence over `.env` file values. This is useful for CI/CD pipelines or when you want to override specific settings without modifying the `.env` file.

## Writing Tests

### Creating a New Test Class

```python
import pytest
from rest_api_testing import BaseApiTest

class TestMyAPI(BaseApiTest):
    """Example API test class"""
    
    async def test_get_endpoint(self):
        """Test GET endpoint"""
        request = await self.authenticated_request()
        response = request.get("/my/endpoint")
        
        await response.should_have.status_code(200)
        await response.should_have.json_path("data.id", exists=True)
        await response.should_have.json_path("data.name", equals="expected_value")
```

### Using Templates with CSV Data

Create Jinja2 template files (`.j2` extension) in `templates/` directory:

**Example: `templates/user-create.json.j2`**
```json
{
  "firstName": "{{ firstName }}",
  "lastName": "{{ lastName }}",
  "email": "{{ email }}",
  "age": {{ age }}
{% if phoneNumber %}
  ,"phoneNumber": "{{ phoneNumber }}"
{% endif %}
}
```

**Example: `templates/user-data.csv`**
```csv
firstName,lastName,email,age,phoneNumber
John,Doe,john.doe@example.com,30,555-1234
Jane,Smith,jane.smith@example.com,25,555-5678
```

**Usage in test:**
```python
async def test_create_user(self):
    """Test creating a user from CSV data"""
    # Load first row from CSV
    user_data = self.load_csv_as_dict("templates/user-data.csv")
    
    # Render template with CSV data
    json_body = self.render_template("templates/user-create.json.j2", user_data)
    
    # Make authenticated POST request
    request = await self.authenticated_request()
    response = request.post("/users", body=json_body)
    
    await response.should_have.status_code(201)
    await response.should_have.json_path("id", exists=True)
```

### Pythonic Response Validation

The framework provides a Pythonic API for response validation:

```python
async def test_response_validation(self):
    """Example of Pythonic response validation"""
    request = await self.authenticated_request()
    response = request.get("/users/123")
    
    # Fluent validation API
    await response.should_have.status_code(200)
    await response.should_have.content_type("application/json")
    
    # JSON path validation
    await response.should_have.json_path("id", equals=123)
    await response.should_have.json_path("name", exists=True)
    await response.should_have.json_path("email", matches=r"^[^@]+@[^@]+\.[^@]+$")
    
    # Extract values
    user_id = await response.json_path("id")
    user_name = await response.json_path("name")
    
    # Custom validation with callables
    await response.should_have.json_path("age", validate=lambda x: 18 <= x <= 100)
    
    # Multiple status codes
    await response.should_have.status_code_in([200, 201])
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_my_api.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=rest_api_testing
```

## Logging

The framework automatically logs test execution details:

- **Configuration logging** - Full configuration (with sensitive values masked) is logged at test suite startup
- **Request logging** - All HTTP requests are logged with method, URL, headers, and body
- **Response logging** - All HTTP responses are logged with status, headers, and body
- **File logging** - Logs are written to timestamped files in the configured log directory (default: `logs/`)
- **Console logging** - Logs are also output to the console

Log files are automatically rotated (10MB per file, 5 backups) and can be configured via `.env`:

```env
LOG_DIRECTORY=logs
LOG_LEVEL=INFO
LOG_REQUEST_BODY=true
LOG_RESPONSE_BODY=true
LOG_MASK_SENSITIVE_HEADERS=true
```

## Dependencies

- **Playwright** - API and browser testing
- **pytest** - Testing framework
- **Jinja2** - Template engine for JSON generation
- **pydantic** - Configuration and data validation
- **pydantic-settings** - Settings management
- **python-dotenv** - Environment variable management

## License

This is a proprietary testing framework for internal use.

## Support

For issues and questions, please contact the application engineering team.

