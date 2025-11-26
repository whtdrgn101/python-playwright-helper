"""Fluent API for making HTTP requests with Playwright."""

import json
import logging
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from playwright.sync_api import APIRequestContext, APIResponse

if TYPE_CHECKING:
    from rest_api_testing.playwright_api.response_validator import ResponseValidator

logger = logging.getLogger(__name__)


class PlaywrightApiRequest:
    """Fluent API builder for making HTTP requests with Playwright."""

    def __init__(self, context: APIRequestContext):
        """Initialize the API request builder."""
        self._context = context
        self._method: Optional[str] = None
        self._url: Optional[str] = None
        self._body: Optional[Union[str, Dict, Any]] = None
        self._headers: Dict[str, str] = {}
        self._query_params: Dict[str, str] = {}
        self._response: Optional[APIResponse] = None
        self._json_response: Optional[Dict] = None
        # Lazy load config to avoid circular imports
        self._config = None

    # HTTP Method Builders
    def get(self, url: str) -> "PlaywrightApiRequest":
        """Set HTTP method to GET."""
        self._method = "GET"
        self._url = url
        return self

    def post(self, url: str, body: Optional[Union[str, Dict, Any]] = None) -> "PlaywrightApiRequest":
        """Set HTTP method to POST."""
        self._method = "POST"
        self._url = url
        if body is not None:
            self._body = body
        return self

    def put(self, url: str, body: Optional[Union[str, Dict, Any]] = None) -> "PlaywrightApiRequest":
        """Set HTTP method to PUT."""
        self._method = "PUT"
        self._url = url
        if body is not None:
            self._body = body
        return self

    def delete(self, url: str) -> "PlaywrightApiRequest":
        """Set HTTP method to DELETE."""
        self._method = "DELETE"
        self._url = url
        return self

    def patch(self, url: str, body: Optional[Union[str, Dict, Any]] = None) -> "PlaywrightApiRequest":
        """Set HTTP method to PATCH."""
        self._method = "PATCH"
        self._url = url
        if body is not None:
            self._body = body
        return self

    # Request Configuration
    def body(self, body: Union[str, Dict, Any]) -> "PlaywrightApiRequest":
        """Set request body."""
        self._body = body
        return self

    def header(self, name: str, value: str) -> "PlaywrightApiRequest":
        """Add a header to the request."""
        self._headers[name] = value
        return self

    def headers(self, headers: Dict[str, str]) -> "PlaywrightApiRequest":
        """Add multiple headers to the request."""
        self._headers.update(headers)
        return self

    def query_param(self, name: str, value: str) -> "PlaywrightApiRequest":
        """Add a query parameter to the request."""
        self._query_params[name] = value
        return self

    def query_params(self, params: Dict[str, str]) -> "PlaywrightApiRequest":
        """Add multiple query parameters to the request."""
        self._query_params.update(params)
        return self

    def _get_config(self):
        """Lazy load config to avoid circular imports."""
        if self._config is None:
            from rest_api_testing.config import get_config
            self._config = get_config()
        return self._config

    def _mask_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive headers for logging."""
        config = self._get_config()
        if not config.log_mask_sensitive_headers:
            return headers

        masked = headers.copy()
        sensitive_keys = ["authorization", "x-api-key", "api-key", "cookie"]
        for key in masked.keys():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                value = masked[key]
                if value:
                    # Show first few chars and mask the rest
                    if len(value) > 10:
                        masked[key] = value[:10] + "***"
                    else:
                        masked[key] = "***"
        return masked

    def _log_request(self) -> None:
        """Log request details."""
        config = self._get_config()
        logger.info("-" * 80)
        logger.info("REQUEST: %s %s", self._method, self._url)
        logger.info("-" * 80)

        # Log headers (masked if configured)
        if self._headers:
            masked_headers = self._mask_sensitive_headers(self._headers)
            logger.info("Headers:")
            for key, value in masked_headers.items():
                logger.info("  %s: %s", key, value)

        # Log query parameters
        if self._query_params:
            logger.info("Query Parameters:")
            for key, value in self._query_params.items():
                logger.info("  %s: %s", key, value)

        # Log body if configured
        if config.log_request_body and self._body is not None:
            logger.info("Request Body:")
            try:
                if isinstance(self._body, dict):
                    body_str = json.dumps(self._body, indent=2)
                elif isinstance(self._body, str):
                    # Try to pretty-print if it's JSON
                    try:
                        body_dict = json.loads(self._body)
                        body_str = json.dumps(body_dict, indent=2)
                    except (json.JSONDecodeError, TypeError):
                        body_str = self._body
                else:
                    body_str = str(self._body)
                # Log body with indentation
                for line in body_str.split("\n"):
                    logger.info("  %s", line)
            except Exception as e:
                logger.warning("Failed to format request body for logging: %s", e)
                logger.info("  %s", str(self._body)[:500])  # First 500 chars

    def _log_response(self) -> None:
        """Log response details."""
        if self._response is None:
            return

        config = self._get_config()
        logger.info("-" * 80)
        logger.info("RESPONSE: %d %s", self._response.status, self._response.status_text)
        logger.info("-" * 80)

        # Log response headers
        response_headers = dict(self._response.headers)
        if response_headers:
            logger.info("Response Headers:")
            for key, value in response_headers.items():
                logger.info("  %s: %s", key, value)

        # Log response body if configured
        if config.log_response_body:
            try:
                content_type = self._response.headers.get("content-type", "")
                response_text = self._response.text()

                if response_text:
                    logger.info("Response Body:")
                    # Try to pretty-print JSON
                    if "application/json" in content_type:
                        try:
                            body_dict = json.loads(response_text)
                            body_str = json.dumps(body_dict, indent=2)
                            for line in body_str.split("\n"):
                                logger.info("  %s", line)
                        except (json.JSONDecodeError, TypeError):
                            # Not valid JSON, log as-is (truncated if too long)
                            if len(response_text) > 1000:
                                logger.info("  %s... (truncated)", response_text[:1000])
                            else:
                                for line in response_text.split("\n"):
                                    logger.info("  %s", line)
                    else:
                        # Non-JSON response, log truncated
                        if len(response_text) > 1000:
                            logger.info("  %s... (truncated, %d chars total)", response_text[:1000], len(response_text))
                        else:
                            for line in response_text.split("\n"):
                                logger.info("  %s", line)
            except Exception as e:
                logger.warning("Failed to log response body: %s", e)

        logger.info("-" * 80)

    # Execute the request
    def _execute(self) -> APIResponse:
        """Execute the HTTP request."""
        if self._method is None or self._url is None:
            raise ValueError("HTTP method and URL must be set before execution")

        # Prepare request options
        options: Dict[str, Any] = {}

        # Handle body
        if self._body is not None:
            if isinstance(self._body, dict):
                options["data"] = json.dumps(self._body)
                if "Content-Type" not in self._headers:
                    self._headers["Content-Type"] = "application/json"
            elif isinstance(self._body, str):
                options["data"] = self._body
            else:
                options["data"] = json.dumps(self._body)
                if "Content-Type" not in self._headers:
                    self._headers["Content-Type"] = "application/json"

        # Add headers
        if self._headers:
            options["headers"] = self._headers

        # Build query string
        if self._query_params:
            query_parts = [f"{k}={v}" for k, v in self._query_params.items()]
            separator = "&" if "?" in self._url else "?"
            self._url = f"{self._url}{separator}{'&'.join(query_parts)}"

        # Log request details
        self._log_request()

        # Execute request based on method
        method_map = {
            "GET": self._context.get,
            "POST": self._context.post,
            "PUT": self._context.put,
            "DELETE": self._context.delete,
            "PATCH": self._context.patch,
        }

        if self._method not in method_map:
            raise ValueError(f"Unsupported HTTP method: {self._method}")

        self._response = method_map[self._method](self._url, **options)

        # Parse JSON response if content type is JSON
        content_type = self._response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                response_text = self._response.text()
                if response_text:
                    self._json_response = json.loads(response_text)
            except Exception as e:
                logger.warning("Failed to parse JSON response: %s", e)

        # Log response details
        self._log_response()

        return self._response

    # Response validation builder
    @property
    def should_have(self) -> "ResponseValidator":
        """Get response validator for fluent validation."""
        if self._response is None:
            self._execute()
        from rest_api_testing.playwright_api.response_validator import ResponseValidator
        return ResponseValidator(self)

    # Response extraction
    @property
    def extract(self) -> "ResponseExtractor":
        """Get response extractor for extracting values."""
        if self._response is None:
            self._execute()
        return ResponseExtractor(self)

    # Getter methods
    @property
    def response(self) -> APIResponse:
        """Get the API response."""
        if self._response is None:
            self._execute()
        return self._response

    @property
    def json(self) -> Optional[Dict]:
        """Get the JSON response as a dictionary."""
        if self._json_response is None and self._response is not None:
            try:
                response_text = self._response.text()
                if response_text:
                    self._json_response = json.loads(response_text)
            except Exception as e:
                logger.warning("Failed to parse JSON response: %s", e)
        return self._json_response

    def json_path(self, path: str, default: Any = None) -> Any:
        """
        Extract a value from JSON response using a JSON path.

        Args:
            path: JSON path (e.g., "data.id" or "/data/id")
            default: Default value if path not found

        Returns:
            Value at the JSON path, or default if not found
        """
        json_data = self.json
        if json_data is None:
            return default

        # Normalize path
        if path.startswith("/"):
            path = path[1:]

        # Navigate through the path
        current = json_data
        for part in path.split("/"):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index] if 0 <= index < len(current) else None
                except ValueError:
                    return default
            else:
                return default

            if current is None:
                return default

        return current


class ResponseExtractor:
    """Response extraction utilities."""

    def __init__(self, request: PlaywrightApiRequest):
        """Initialize the response extractor."""
        self._request = request

    @property
    def response(self) -> APIResponse:
        """Get the raw API response."""
        return self._request.response

    def as_string(self) -> str:
        """Get response as string."""
        return self._request.response.text()

    def as_json(self) -> Optional[Dict]:
        """Get response as JSON dictionary."""
        return self._request.json

    def as_dict(self) -> Optional[Dict]:
        """Get response as dictionary (alias for as_json)."""
        return self._request.json

    def path(self, json_path: str, default: Any = None) -> Any:
        """Extract value from JSON response using JSON path."""
        return self._request.json_path(json_path, default)

