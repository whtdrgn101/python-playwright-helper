"""Async property wrappers for fluent API pattern."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rest_api_testing.playwright_api.playwright_api_request import PlaywrightApiRequest
    from rest_api_testing.playwright_api.response_validator import ResponseValidator
    from rest_api_testing.playwright_api.playwright_api_request import ResponseExtractor
    from playwright.async_api import APIResponse


class AsyncShouldHave:
    """Wrapper to make should_have work as a property with async methods."""
    
    def __init__(self, request: "PlaywrightApiRequest"):
        """Initialize the async should_have wrapper."""
        self._request = request
        self._validator = None
    
    async def _ensure_validator(self):
        """Ensure validator is created."""
        if self._validator is None:
            if self._request._response is None:
                await self._request._execute()
            from rest_api_testing.playwright_api.response_validator import ResponseValidator
            self._validator = ResponseValidator(self._request)
        return self._validator
    
    async def status_code(self, expected):
        """Validate status code."""
        validator = await self._ensure_validator()
        return await validator.status_code(expected)
    
    async def status_code_in(self, expected_codes):
        """Validate status code is in list."""
        validator = await self._ensure_validator()
        return await validator.status_code_in(expected_codes)
    
    async def content_type(self, expected):
        """Validate content type."""
        validator = await self._ensure_validator()
        return await validator.content_type(expected)
    
    async def header(self, name, expected):
        """Validate header."""
        validator = await self._ensure_validator()
        return await validator.header(name, expected)
    
    async def json_path(self, path, equals=None, exists=None, matches=None, validate=None):
        """Validate JSON path."""
        validator = await self._ensure_validator()
        return await validator.json_path(path, equals=equals, exists=exists, matches=matches, validate=validate)


class AsyncExtract:
    """Wrapper to make extract work as a property with async methods."""
    
    def __init__(self, request: "PlaywrightApiRequest"):
        """Initialize the async extract wrapper."""
        self._request = request
        self._extractor = None
    
    async def _ensure_extractor(self):
        """Ensure extractor is created."""
        if self._extractor is None:
            if self._request._response is None:
                await self._request._execute()
            from rest_api_testing.playwright_api.playwright_api_request import ResponseExtractor
            self._extractor = ResponseExtractor(self._request)
        return self._extractor
    
    async def as_string(self):
        """Get response as string."""
        extractor = await self._ensure_extractor()
        return await extractor.as_string()
    
    async def as_json(self):
        """Get response as JSON."""
        extractor = await self._ensure_extractor()
        return await extractor.as_json()
    
    async def as_dict(self):
        """Get response as dictionary."""
        extractor = await self._ensure_extractor()
        return await extractor.as_dict()
    
    async def path(self, json_path, default=None):
        """Extract value from JSON path."""
        extractor = await self._ensure_extractor()
        return await extractor.path(json_path, default)


class AsyncResponse:
    """Wrapper to make response work as a property with async access."""
    
    def __init__(self, request: "PlaywrightApiRequest"):
        """Initialize the async response wrapper."""
        self._request = request
    
    async def __call__(self) -> "APIResponse":
        """Get the API response."""
        return await self._request._ensure_response()
    
    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access - will need to await response first."""
        raise RuntimeError(
            f"Cannot access '{name}' directly. Use 'await response.response()' first, "
            f"or access properties like 'response.status' after awaiting."
        )
