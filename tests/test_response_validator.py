"""Unit tests for ResponseValidator."""

import pytest
import re
from unittest.mock import AsyncMock, MagicMock, patch
from playwright.async_api import APIResponse
from rest_api_testing.playwright_api.response_validator import ResponseValidator
from rest_api_testing.playwright_api import PlaywrightApiRequest


@pytest.fixture
def mock_request():
    """Create a mock PlaywrightApiRequest."""
    return MagicMock(spec=PlaywrightApiRequest)


@pytest.fixture
def mock_response():
    """Create a mock APIResponse."""
    response = AsyncMock(spec=APIResponse)
    response.status = 200
    response.status_text = "OK"
    response.headers = {
        "content-type": "application/json",
        "x-request-id": "req-12345"
    }
    response.text = AsyncMock(return_value='{"result": "success", "id": 123}')
    return response


@pytest.fixture
def validator(mock_request, mock_response):
    """Create a ResponseValidator with mocked request."""
    mock_request.response = AsyncMock(return_value=mock_response)
    mock_request.json = AsyncMock(return_value={"result": "success", "id": 123})
    return ResponseValidator(mock_request)


class TestStatusCodeValidation:
    """Test status code validation."""

    @pytest.mark.asyncio
    async def test_validate_status_code_success(self, validator, mock_response):
        """Test validating correct status code."""
        mock_response.status = 200
        result = await validator.status_code(200)
        
        assert result is validator  # Check fluent API returns self

    @pytest.mark.asyncio
    async def test_validate_status_code_failure(self, validator, mock_response):
        """Test validating incorrect status code."""
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        
        with pytest.raises(AssertionError) as exc_info:
            await validator.status_code(200)
        
        assert "404" in str(exc_info.value)
        assert "200" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_status_code_list(self, validator, mock_response):
        """Test validating status code against list."""
        mock_response.status = 201
        
        result = await validator.status_code([200, 201, 202])
        assert result is validator

    @pytest.mark.asyncio
    async def test_validate_status_code_list_failure(self, validator, mock_response):
        """Test validation fails when status code not in list."""
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Server Error")
        
        with pytest.raises(AssertionError) as exc_info:
            await validator.status_code([200, 201, 202])
        
        assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_status_code_in_method(self, validator, mock_response):
        """Test status_code_in convenience method."""
        mock_response.status = 201
        
        result = await validator.status_code_in([200, 201, 202])
        assert result is validator

    @pytest.mark.asyncio
    async def test_validate_various_status_codes(self, validator, mock_response):
        """Test validation of various status codes."""
        for status in [200, 201, 202, 204, 301, 302, 400, 401, 403, 404, 500, 502, 503]:
            mock_response.status = status
            result = await validator.status_code(status)
            assert result is validator


class TestContentTypeValidation:
    """Test content type validation."""

    @pytest.mark.asyncio
    async def test_validate_content_type_json(self, validator, mock_response):
        """Test validating JSON content type."""
        mock_response.headers = {"content-type": "application/json"}
        
        result = await validator.content_type("application/json")
        assert result is validator

    @pytest.mark.asyncio
    async def test_validate_content_type_partial_match(self, validator, mock_response):
        """Test content type validation with partial match."""
        mock_response.headers = {"content-type": "application/json; charset=utf-8"}
        
        result = await validator.content_type("application/json")
        assert result is validator

    @pytest.mark.asyncio
    async def test_validate_content_type_failure(self, validator, mock_response):
        """Test content type validation failure."""
        mock_response.headers = {"content-type": "text/html"}
        
        with pytest.raises(AssertionError) as exc_info:
            await validator.content_type("application/json")
        
        assert "application/json" in str(exc_info.value)
        assert "text/html" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_content_type_xml(self, validator, mock_response):
        """Test validating XML content type."""
        mock_response.headers = {"content-type": "application/xml"}
        
        result = await validator.content_type("application/xml")
        assert result is validator

    @pytest.mark.asyncio
    async def test_validate_content_type_missing(self, validator, mock_response):
        """Test validation when content-type header is missing."""
        mock_response.headers = {}
        
        with pytest.raises(AssertionError):
            await validator.content_type("application/json")


class TestHeaderValidation:
    """Test header validation."""

    @pytest.mark.asyncio
    async def test_validate_header_success(self, validator, mock_response):
        """Test validating correct header value."""
        mock_response.headers = {"x-request-id": "req-12345"}
        
        result = await validator.header("x-request-id", "req-12345")
        assert result is validator

    @pytest.mark.asyncio
    async def test_validate_header_failure(self, validator, mock_response):
        """Test header validation failure."""
        mock_response.headers = {"x-request-id": "req-12345"}
        
        with pytest.raises(AssertionError) as exc_info:
            await validator.header("x-request-id", "req-99999")
        
        assert "x-request-id" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_header_missing(self, validator, mock_response):
        """Test validation when header is missing."""
        mock_response.headers = {}
        
        # Missing header returns empty string, so should fail
        with pytest.raises(AssertionError):
            await validator.header("x-request-id", "req-12345")

    @pytest.mark.asyncio
    async def test_validate_multiple_headers(self, validator, mock_response):
        """Test validating multiple headers."""
        mock_response.headers = {
            "content-type": "application/json",
            "x-request-id": "req-12345",
            "x-custom": "custom-value"
        }
        
        await validator.header("content-type", "application/json")
        await validator.header("x-request-id", "req-12345")
        result = await validator.header("x-custom", "custom-value")
        
        assert result is validator


class TestJSONPathValidation:
    """Test JSON path validation."""

    @pytest.mark.asyncio
    async def test_json_path_equals_simple(self, validator):
        """Test JSON path equality check on simple value."""
        result = await validator.json_path("result", equals="success")
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_equals_number(self, validator):
        """Test JSON path equality check on number."""
        result = await validator.json_path("id", equals=123)
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_equals_failure(self, validator):
        """Test JSON path equality check failure."""
        with pytest.raises(AssertionError) as exc_info:
            await validator.json_path("result", equals="failure")
        
        assert "expected" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_json_path_exists_true(self, validator):
        """Test JSON path existence check - path exists."""
        result = await validator.json_path("result", exists=True)
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_exists_false(self, validator):
        """Test JSON path existence check - path should not exist."""
        result = await validator.json_path("nonexistent", exists=False)
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_exists_false_but_exists(self, validator):
        """Test JSON path should not exist but does."""
        with pytest.raises(AssertionError):
            await validator.json_path("result", exists=False)

    @pytest.mark.asyncio
    async def test_json_path_nested(self, validator):
        """Test JSON path on nested object."""
        validator._request.json = AsyncMock(return_value={
            "user": {
                "id": 123,
                "name": "John",
                "email": "john@example.com"
            }
        })
        
        result = await validator.json_path("user/name", equals="John")
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_array_index(self, validator):
        """Test JSON path with array index."""
        validator._request.json = AsyncMock(return_value={
            "items": ["apple", "banana", "cherry"]
        })
        
        result = await validator.json_path("items/0", equals="apple")
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_array_nested_object(self, validator):
        """Test JSON path with array of objects."""
        validator._request.json = AsyncMock(return_value={
            "users": [
                {"id": 1, "name": "John"},
                {"id": 2, "name": "Jane"}
            ]
        })
        
        result = await validator.json_path("users/1/name", equals="Jane")
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_with_slash_prefix(self, validator):
        """Test JSON path with leading slash (JSONPath style)."""
        result = await validator.json_path("/result", equals="success")
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_not_found(self, validator):
        """Test JSON path that doesn't exist."""
        with pytest.raises(AssertionError) as exc_info:
            await validator.json_path("nonexistent/path", equals="value")
        
        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_json_path_no_json_response(self, validator):
        """Test JSON path validation when response is not JSON."""
        validator._request.json = AsyncMock(return_value=None)
        
        with pytest.raises(AssertionError) as exc_info:
            await validator.json_path("some/path", equals="value")
        
        assert "not json" in str(exc_info.value).lower()


class TestJSONPathRegexMatching:
    """Test JSON path validation with regex."""

    @pytest.mark.asyncio
    async def test_json_path_matches_string_pattern(self, validator):
        """Test JSON path regex matching with string pattern."""
        result = await validator.json_path("result", matches="succe.*")
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_matches_compiled_pattern(self, validator):
        """Test JSON path regex matching with compiled pattern."""
        pattern = re.compile(r"^success$")
        result = await validator.json_path("result", matches=pattern)
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_matches_failure(self, validator):
        """Test JSON path regex matching failure."""
        with pytest.raises(AssertionError) as exc_info:
            await validator.json_path("result", matches="^fail.*")
        
        assert "does not match" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_json_path_matches_on_number(self, validator):
        """Test JSON path regex matching on number value."""
        result = await validator.json_path("id", matches=r"^\d+$")
        assert result is validator


class TestJSONPathCustomValidation:
    """Test JSON path with custom validation function."""

    @pytest.mark.asyncio
    async def test_json_path_custom_validation_pass(self, validator):
        """Test JSON path with custom validation function that passes."""
        def is_positive(val):
            return val > 0
        
        result = await validator.json_path("id", validate=is_positive)
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_custom_validation_fail(self, validator):
        """Test JSON path with custom validation function that fails."""
        def is_negative(val):
            return val < 0
        
        with pytest.raises(AssertionError) as exc_info:
            await validator.json_path("id", validate=is_negative)
        
        assert "custom validation failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_json_path_custom_validation_string_check(self, validator):
        """Test custom validation on string value."""
        def is_uppercase(val):
            return isinstance(val, str) and val.isupper()
        
        with pytest.raises(AssertionError):
            await validator.json_path("result", validate=is_uppercase)

    @pytest.mark.asyncio
    async def test_json_path_custom_validation_length(self, validator):
        """Test custom validation checking string length."""
        def is_short(val):
            return len(str(val)) < 10
        
        result = await validator.json_path("result", validate=is_short)
        assert result is validator


class TestFluentChaining:
    """Test fluent API chaining of validators."""

    @pytest.mark.asyncio
    async def test_chain_status_and_content_type(self, validator, mock_response):
        """Test chaining status code and content type validation."""
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/json"}
        
        await validator.status_code(200)
        result = await validator.content_type("application/json")
        
        assert result is validator

    @pytest.mark.asyncio
    async def test_chain_multiple_json_paths(self, validator):
        """Test chaining multiple JSON path validations."""
        validator._request.json = AsyncMock(return_value={
            "status": "success",
            "data": {
                "id": 123,
                "name": "Test"
            }
        })
        
        await validator.json_path("status", equals="success")
        await validator.json_path("data/id", equals=123)
        result = await validator.json_path("data/name", equals="Test")
        
        assert result is validator

    @pytest.mark.asyncio
    async def test_chain_status_headers_and_json(self, validator, mock_response):
        """Test chaining status, header, and JSON path validation."""
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/json"}
        
        await validator.status_code(200)
        await validator.header("content-type", "application/json")
        result = await validator.json_path("result", equals="success")
        
        assert result is validator


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_json_path_with_empty_dict(self, validator):
        """Test JSON path with empty response object."""
        validator._request.json = AsyncMock(return_value={})
        
        with pytest.raises(AssertionError):
            await validator.json_path("any_field", exists=True)

    @pytest.mark.asyncio
    async def test_json_path_with_empty_string(self, validator):
        """Test JSON path with empty string value."""
        validator._request.json = AsyncMock(return_value={"field": ""})
        
        result = await validator.json_path("field", equals="")
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_with_zero(self, validator):
        """Test JSON path with zero value."""
        validator._request.json = AsyncMock(return_value={"count": 0})
        
        result = await validator.json_path("count", equals=0)
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_with_boolean_true(self, validator):
        """Test JSON path with boolean true."""
        validator._request.json = AsyncMock(return_value={"success": True})
        
        result = await validator.json_path("success", equals=True)
        assert result is validator

    @pytest.mark.asyncio
    async def test_json_path_with_boolean_false(self, validator):
        """Test JSON path with boolean false."""
        validator._request.json = AsyncMock(return_value={"success": False})
        
        result = await validator.json_path("success", equals=False)
        assert result is validator

    @pytest.mark.asyncio
    async def test_array_index_out_of_bounds(self, validator):
        """Test JSON path with array index out of bounds."""
        validator._request.json = AsyncMock(return_value={
            "items": ["a", "b", "c"]
        })
        
        with pytest.raises(AssertionError):
            await validator.json_path("items/99", equals="value")
