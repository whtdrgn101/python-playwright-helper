"""Unit tests for PlaywrightApiRequest."""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from playwright.async_api import APIRequestContext, APIResponse
from rest_api_testing.playwright_api import PlaywrightApiRequest


@pytest.fixture
def mock_api_context():
    """Create a mock APIRequestContext."""
    return AsyncMock(spec=APIRequestContext)


@pytest.fixture
def mock_response():
    """Create a mock APIResponse."""
    response = AsyncMock(spec=APIResponse)
    response.status = 200
    response.status_text = "OK"
    response.headers = {"content-type": "application/json"}
    response.text = AsyncMock(return_value='{"result": "success"}')
    return response


@pytest.fixture
def api_request(mock_api_context):
    """Create a PlaywrightApiRequest instance."""
    return PlaywrightApiRequest(mock_api_context)


class TestHTTPMethods:
    """Test HTTP method builders."""

    def test_get_method(self, api_request):
        """Test GET method builder."""
        result = api_request.get("https://api.example.com/users")
        
        assert result is api_request  # Fluent API returns self
        assert api_request._method == "GET"
        assert api_request._url == "https://api.example.com/users"

    def test_post_method(self, api_request):
        """Test POST method builder."""
        body = {"name": "John"}
        result = api_request.post("https://api.example.com/users", body)
        
        assert result is api_request
        assert api_request._method == "POST"
        assert api_request._url == "https://api.example.com/users"
        assert api_request._body == body

    def test_post_method_no_body(self, api_request):
        """Test POST method without body."""
        result = api_request.post("https://api.example.com/users")
        
        assert api_request._method == "POST"
        assert api_request._body is None

    def test_put_method(self, api_request):
        """Test PUT method builder."""
        body = {"name": "Jane"}
        result = api_request.put("https://api.example.com/users/1", body)
        
        assert api_request._method == "PUT"
        assert api_request._url == "https://api.example.com/users/1"
        assert api_request._body == body

    def test_delete_method(self, api_request):
        """Test DELETE method builder."""
        result = api_request.delete("https://api.example.com/users/1")
        
        assert api_request._method == "DELETE"
        assert api_request._url == "https://api.example.com/users/1"

    def test_patch_method(self, api_request):
        """Test PATCH method builder."""
        body = {"status": "inactive"}
        result = api_request.patch("https://api.example.com/users/1", body)
        
        assert api_request._method == "PATCH"
        assert api_request._url == "https://api.example.com/users/1"
        assert api_request._body == body


class TestRequestConfiguration:
    """Test request configuration methods."""

    def test_body_builder(self, api_request):
        """Test body builder method."""
        body = {"key": "value"}
        result = api_request.body(body)
        
        assert result is api_request
        assert api_request._body == body

    def test_body_with_string(self, api_request):
        """Test setting body as string."""
        body = '{"key": "value"}'
        api_request.body(body)
        assert api_request._body == body

    def test_single_header(self, api_request):
        """Test adding single header."""
        result = api_request.header("Authorization", "Bearer token123")
        
        assert result is api_request
        assert api_request._headers["Authorization"] == "Bearer token123"

    def test_multiple_headers(self, api_request):
        """Test adding multiple headers via headers method."""
        headers = {
            "Authorization": "Bearer token123",
            "Content-Type": "application/json",
            "X-Custom-Header": "value"
        }
        result = api_request.headers(headers)
        
        assert result is api_request
        assert api_request._headers == headers

    def test_headers_merge(self, api_request):
        """Test that multiple header calls merge headers."""
        api_request.header("Authorization", "Bearer token")
        api_request.header("X-Custom", "custom-value")
        
        assert len(api_request._headers) == 2
        assert api_request._headers["Authorization"] == "Bearer token"
        assert api_request._headers["X-Custom"] == "custom-value"

    def test_single_query_param(self, api_request):
        """Test adding single query parameter."""
        result = api_request.query_param("page", "1")
        
        assert result is api_request
        assert api_request._query_params["page"] == "1"

    def test_multiple_query_params(self, api_request):
        """Test adding multiple query parameters."""
        params = {
            "page": "1",
            "limit": "10",
            "sort": "name"
        }
        result = api_request.query_params(params)
        
        assert result is api_request
        assert api_request._query_params == params

    def test_query_params_merge(self, api_request):
        """Test that multiple query param calls merge params."""
        api_request.query_param("page", "1")
        api_request.query_param("limit", "10")
        
        assert len(api_request._query_params) == 2
        assert api_request._query_params["page"] == "1"
        assert api_request._query_params["limit"] == "10"


class TestFluentAPIChaining:
    """Test fluent API chaining."""

    def test_chained_method_calls(self, api_request):
        """Test chaining multiple method calls."""
        result = (api_request
                 .post("https://api.example.com/users")
                 .header("Authorization", "Bearer token")
                 .header("Content-Type", "application/json")
                 .query_param("notify", "true")
                 .body({"name": "John"}))
        
        assert result is api_request
        assert api_request._method == "POST"
        assert api_request._headers["Authorization"] == "Bearer token"
        assert api_request._query_params["notify"] == "true"

    def test_get_chained_with_headers(self, api_request):
        """Test GET request with headers."""
        result = (api_request
                 .get("https://api.example.com/users")
                 .header("Authorization", "Bearer token")
                 .query_param("page", "1"))
        
        assert api_request._method == "GET"
        assert api_request._headers["Authorization"] == "Bearer token"
        assert api_request._query_params["page"] == "1"


class TestRequestExecution:
    """Test request execution."""

    @pytest.mark.asyncio
    async def test_execute_missing_method(self, api_request):
        """Test execution without method set."""
        api_request._url = "https://api.example.com"
        
        with pytest.raises(ValueError) as exc_info:
            await api_request._execute()
        assert "HTTP method" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_missing_url(self, api_request):
        """Test execution without URL set."""
        api_request._method = "GET"
        
        with pytest.raises(ValueError) as exc_info:
            await api_request._execute()
        assert "URL" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_get_request(self, api_request, mock_api_context, mock_response):
        """Test GET request execution."""
        mock_api_context.get = AsyncMock(return_value=mock_response)
        
        api_request.get("https://api.example.com/users")
        response = await api_request._execute()
        
        assert response is mock_response
        mock_api_context.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_post_with_json_body(self, api_request, mock_api_context, mock_response):
        """Test POST request with JSON body."""
        mock_api_context.post = AsyncMock(return_value=mock_response)
        
        body = {"name": "John", "email": "john@example.com"}
        api_request.post("https://api.example.com/users", body)
        
        with patch.object(api_request, '_log_request'):
            with patch.object(api_request, '_log_response', new_callable=AsyncMock):
                response = await api_request._execute()
        
        assert response is mock_response
        # Verify Content-Type header was added
        assert api_request._headers.get("Content-Type") == "application/json"

    @pytest.mark.asyncio
    async def test_execute_with_query_params(self, api_request, mock_api_context, mock_response):
        """Test request with query parameters."""
        mock_api_context.get = AsyncMock(return_value=mock_response)
        
        api_request.get("https://api.example.com/users")
        api_request.query_param("page", "2")
        api_request.query_param("limit", "10")
        
        with patch.object(api_request, '_log_request'):
            with patch.object(api_request, '_log_response', new_callable=AsyncMock):
                response = await api_request._execute()
        
        # Verify query params were appended to URL
        call_args = mock_api_context.get.call_args
        assert "page=2" in call_args[0][0]
        assert "limit=10" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_execute_post_with_string_body(self, api_request, mock_api_context, mock_response):
        """Test POST with string body."""
        mock_api_context.post = AsyncMock(return_value=mock_response)
        
        body_str = '{"name": "John"}'
        api_request.post("https://api.example.com/users", body_str)
        
        with patch.object(api_request, '_log_request'):
            with patch.object(api_request, '_log_response', new_callable=AsyncMock):
                response = await api_request._execute()
        
        assert response is mock_response

    @pytest.mark.asyncio
    async def test_execute_unsupported_method(self, api_request):
        """Test execution with unsupported HTTP method."""
        api_request._method = "UNKNOWN"
        api_request._url = "https://api.example.com"
        
        with pytest.raises(ValueError) as exc_info:
            await api_request._execute()
        assert "Unsupported HTTP method" in str(exc_info.value)


class TestMaskSensitiveHeaders:
    """Test sensitive header masking."""

    def test_mask_authorization_header(self, api_request):
        """Test masking authorization header."""
        headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "Content-Type": "application/json"
        }
        
        with patch.object(api_request, '_get_config') as mock_config:
            mock_config.return_value.log_mask_sensitive_headers = True
            masked = api_request._mask_sensitive_headers(headers)
        
        assert masked["Authorization"].endswith("***")
        assert masked["Authorization"].startswith("Bearer ")
        assert masked["Content-Type"] == "application/json"

    def test_mask_api_key_header(self, api_request):
        """Test masking API key header."""
        headers = {
            "x-api-key": "sk-1234567890abcdefghij",
            "Accept": "application/json"
        }
        
        with patch.object(api_request, '_get_config') as mock_config:
            mock_config.return_value.log_mask_sensitive_headers = True
            masked = api_request._mask_sensitive_headers(headers)
        
        assert masked["x-api-key"].endswith("***")
        assert masked["Accept"] == "application/json"

    def test_no_mask_when_disabled(self, api_request):
        """Test that masking is disabled when configured."""
        headers = {
            "Authorization": "Bearer secret123",
            "Content-Type": "application/json"
        }
        
        with patch.object(api_request, '_get_config') as mock_config:
            mock_config.return_value.log_mask_sensitive_headers = False
            masked = api_request._mask_sensitive_headers(headers)
        
        assert masked == headers

    def test_mask_short_header_value(self, api_request):
        """Test masking short header values."""
        headers = {
            "x-api-key": "short",
            "Authorization": "token"
        }
        
        with patch.object(api_request, '_get_config') as mock_config:
            mock_config.return_value.log_mask_sensitive_headers = True
            masked = api_request._mask_sensitive_headers(headers)
        
        # Short values should be completely masked
        assert masked["x-api-key"] == "***"
        assert masked["Authorization"] == "***"


class TestLogging:
    """Test request and response logging."""

    def test_log_request_without_body(self, api_request):
        """Test logging request without body."""
        api_request.get("https://api.example.com/users")
        api_request.header("Authorization", "Bearer token")
        
        with patch('rest_api_testing.playwright_api.playwright_api_request.logger') as mock_logger:
            with patch.object(api_request, '_get_config') as mock_config:
                mock_config.return_value.log_request_body = False
                api_request._log_request()
        
        # Verify logging was called
        assert mock_logger.info.called

    def test_log_request_with_json_body(self, api_request):
        """Test logging request with JSON body."""
        body = {"name": "John", "email": "john@example.com"}
        api_request.post("https://api.example.com/users", body)
        
        with patch('rest_api_testing.playwright_api.playwright_api_request.logger') as mock_logger:
            with patch.object(api_request, '_get_config') as mock_config:
                mock_config.return_value.log_request_body = True
                api_request._log_request()
        
        assert mock_logger.info.called

    def test_log_request_with_string_body(self, api_request):
        """Test logging request with string body."""
        api_request.post("https://api.example.com/users", '{"name": "John"}')
        
        with patch('rest_api_testing.playwright_api.playwright_api_request.logger') as mock_logger:
            with patch.object(api_request, '_get_config') as mock_config:
                mock_config.return_value.log_request_body = True
                api_request._log_request()
        
        assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_log_response_json(self, api_request, mock_response):
        """Test logging JSON response."""
        api_request._response = mock_response
        
        with patch('rest_api_testing.playwright_api.playwright_api_request.logger') as mock_logger:
            with patch.object(api_request, '_get_config') as mock_config:
                mock_config.return_value.log_response_body = True
                await api_request._log_response()
        
        assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_log_response_empty_body(self, api_request):
        """Test logging response with empty body."""
        response = AsyncMock(spec=APIResponse)
        response.status = 204
        response.status_text = "No Content"
        response.headers = {}
        response.text = AsyncMock(return_value="")
        
        api_request._response = response
        
        with patch('rest_api_testing.playwright_api.playwright_api_request.logger') as mock_logger:
            with patch.object(api_request, '_get_config') as mock_config:
                mock_config.return_value.log_response_body = True
                await api_request._log_response()
        
        assert mock_logger.info.called


class TestResponseParsing:
    """Test response parsing."""

    @pytest.mark.asyncio
    async def test_json_response_parsing(self, api_request, mock_api_context, mock_response):
        """Test parsing JSON response."""
        mock_api_context.get = AsyncMock(return_value=mock_response)
        
        api_request.get("https://api.example.com/users/1")
        
        with patch.object(api_request, '_log_request'):
            with patch.object(api_request, '_log_response', new_callable=AsyncMock):
                await api_request._execute()
        
        # Verify JSON was parsed
        assert api_request._json_response == {"result": "success"}

    @pytest.mark.asyncio
    async def test_json_direct_access(self, api_request):
        """Test directly accessing parsed JSON."""
        api_request._response = AsyncMock()
        api_request._json_response = {"result": "success", "id": 123}
        
        # Set method and URL so response exists
        api_request._method = "GET"
        api_request._url = "https://api.example.com/test"
        
        result = await api_request.json()
        assert result == {"result": "success", "id": 123}

    @pytest.mark.asyncio
    async def test_json_with_no_parsed_response(self, api_request, mock_api_context):
        """Test getting JSON when response not yet parsed."""
        # Create a response without JSON content
        response = AsyncMock(spec=APIResponse)
        response.status = 204
        response.headers = {"content-type": "text/plain"}
        response.text = AsyncMock(return_value="")
        mock_api_context.get = AsyncMock(return_value=response)
        
        api_request.get("https://api.example.com/test")
        
        with patch.object(api_request, '_log_request'):
            with patch.object(api_request, '_log_response', new_callable=AsyncMock):
                await api_request._execute()
        
        # Should return None for non-JSON response
        result = await api_request.json()
        assert result is None


class TestContextInitialization:
    """Test context initialization."""

    def test_context_stored(self, mock_api_context):
        """Test that context is stored."""
        request = PlaywrightApiRequest(mock_api_context)
        assert request._context is mock_api_context

    def test_initial_state(self, api_request):
        """Test initial state of PlaywrightApiRequest."""
        assert api_request._method is None
        assert api_request._url is None
        assert api_request._body is None
        assert api_request._headers == {}
        assert api_request._query_params == {}
        assert api_request._response is None
        assert api_request._json_response is None
