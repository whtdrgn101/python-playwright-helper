"""Pythonic response validation utilities."""

import logging
import re
from typing import Any, Callable, List, Optional, Union, TYPE_CHECKING
from playwright.async_api import APIResponse

if TYPE_CHECKING:
    from rest_api_testing.playwright_api.playwright_api_request import PlaywrightApiRequest

logger = logging.getLogger(__name__)


class ResponseValidator:
    """Pythonic response validator with fluent API."""

    def __init__(self, request: "PlaywrightApiRequest"):  # type: ignore
        """Initialize the response validator."""
        self._request = request

    async def _response(self) -> APIResponse:
        """Get the API response."""
        return await self._request.response()

    async def _json(self) -> Optional[dict]:
        """Get the JSON response."""
        return await self._request.json()

    async def status_code(self, expected: Union[int, List[int]]) -> "ResponseValidator":
        """
        Validate response status code.

        Args:
            expected: Expected status code(s). Can be a single int or list of ints.

        Returns:
            Self for method chaining

        Raises:
            AssertionError: If status code doesn't match
        """
        response = await self._response()
        actual = response.status
        if isinstance(expected, list):
            if actual not in expected:
                response_text = (await response.text())[:500]  # Limit response text
                raise AssertionError(
                    f"Expected status code to be one of {expected} but got {actual}. "
                    f"Response: {response_text}"
                )
        else:
            if actual != expected:
                response_text = (await response.text())[:500]  # Limit response text
                raise AssertionError(
                    f"Expected status {expected} but got {actual}. Response: {response_text}"
                )
        return self

    async def status_code_in(self, expected_codes: List[int]) -> "ResponseValidator":
        """
        Validate that response status code is in the list of expected codes.

        Args:
            expected_codes: List of acceptable status codes

        Returns:
            Self for method chaining
        """
        return await self.status_code(expected_codes)

    async def content_type(self, expected: str) -> "ResponseValidator":
        """
        Validate response content type.

        Args:
            expected: Expected content type (partial match supported)

        Returns:
            Self for method chaining

        Raises:
            AssertionError: If content type doesn't match
        """
        response = await self._response()
        content_type = response.headers.get("content-type", "")
        if expected not in content_type:
            raise AssertionError(
                f"Expected content type containing '{expected}' but got '{content_type}'"
            )
        return self

    async def header(self, name: str, expected: str) -> "ResponseValidator":
        """
        Validate response header value.

        Args:
            name: Header name (case-insensitive)
            expected: Expected header value

        Returns:
            Self for method chaining

        Raises:
            AssertionError: If header value doesn't match
        """
        response = await self._response()
        actual = response.headers.get(name.lower(), "")
        if actual != expected:
            raise AssertionError(
                f"Header {name}: expected '{expected}' but got '{actual}'"
            )
        return self

    async def json_path(
        self,
        path: str,
        equals: Optional[Any] = None,
        exists: Optional[bool] = None,
        matches: Optional[Union[str, re.Pattern]] = None,
        validate: Optional[Callable[[Any], bool]] = None,
    ) -> "ResponseValidator":
        """
        Validate JSON path in response.

        Args:
            path: JSON path (e.g., "data.id" or "/data/id")
            equals: Expected value (equality check)
            exists: Whether the path should exist (True/False)
            matches: Regex pattern or string to match against
            validate: Custom validation function that takes the value and returns bool

        Returns:
            Self for method chaining

        Raises:
            AssertionError: If validation fails
        """
        json_data = await self._json()
        if json_data is None:
            raise AssertionError("Response is not JSON or could not be parsed")

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
                    current = None
            else:
                current = None

            if current is None:
                if exists is False:
                    return self  # Path doesn't exist, which is what we want
                raise AssertionError(f"JSON path '{path}' not found in response")

        # Check if path exists
        if exists is not None:
            if exists and current is None:
                raise AssertionError(f"JSON path '{path}' does not exist in response")
            if not exists and current is not None:
                raise AssertionError(f"JSON path '{path}' exists but should not")

        # Check equality
        if equals is not None:
            if current != equals:
                raise AssertionError(
                    f"Field {path}: expected '{equals}' but got '{current}'"
                )

        # Check regex match
        if matches is not None:
            pattern = re.compile(matches) if isinstance(matches, str) else matches
            value_str = str(current)
            if not pattern.search(value_str):
                raise AssertionError(
                    f"Field {path}: value '{current}' does not match pattern '{pattern.pattern}'"
                )

        # Custom validation
        if validate is not None:
            if not validate(current):
                raise AssertionError(
                    f"Field {path}: custom validation failed for value '{current}'"
                )

        return self
