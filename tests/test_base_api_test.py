"""Unit tests for BaseApiTest."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from playwright.async_api import Playwright, APIRequestContext
from rest_api_testing.base_api_test import BaseApiTest
from rest_api_testing.config import TestConfig
from rest_api_testing.auth import AuthenticationService
from rest_api_testing.template import TemplateService
from rest_api_testing.playwright_api import PlaywrightApiRequest


@pytest.fixture(autouse=True)
def reset_base_api_test():
    """Reset BaseApiTest singleton state before each test."""
    BaseApiTest._config = None
    BaseApiTest._auth_service = None
    BaseApiTest._template_service = None
    BaseApiTest._playwright_instances = {}
    BaseApiTest._initialized = False
    BaseApiTest._scopes = None
    BaseApiTest._bypass_cache = False
    BaseApiTest._unauthenticated_api_request_context = None
    BaseApiTest._api_request_context = None
    BaseApiTest._playwright_lock = None
    yield
    # Cleanup after test
    BaseApiTest._initialized = False


@pytest.fixture
def mock_config():
    """Create a mock Config instance."""
    config = MagicMock(spec=TestConfig)
    config.api_base_url = "https://api.example.com"
    config.log_directory = "/tmp/logs"
    config.log_level = "INFO"
    config.test_timeout = 30000
    config.log_mask_sensitive_headers = True
    config.log_request_body = True
    config.log_response_body = True
    return config


@pytest.fixture
def mock_auth_service():
    """Create a mock AuthenticationService."""
    service = MagicMock(spec=AuthenticationService)
    service.get_access_token = AsyncMock(return_value="mock-token-123")
    return service


@pytest.fixture
def mock_template_service():
    """Create a mock TemplateService."""
    service = MagicMock(spec=TemplateService)
    service.render = MagicMock(return_value='{"rendered": "data"}')
    return service


@pytest.fixture
def mock_playwright():
    """Create a mock Playwright instance."""
    playwright = MagicMock(spec=Playwright)
    request_context = AsyncMock(spec=APIRequestContext)
    playwright.request = MagicMock()
    playwright.request.new_context = AsyncMock(return_value=request_context)
    return playwright


class TestBaseApiTestInitialization:
    """Test BaseApiTest initialization."""

    @pytest.mark.asyncio
    async def test_ensure_initialized(self, mock_config, mock_auth_service, mock_template_service):
        """Test _ensure_initialized sets up static resources."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
        
        # Verify state is initialized
        assert BaseApiTest._initialized is True
        assert BaseApiTest._config is not None
        assert BaseApiTest._auth_service is not None
        assert BaseApiTest._template_service is not None

    @pytest.mark.asyncio
    async def test_ensure_initialized_idempotent(self, mock_config, mock_auth_service, mock_template_service):
        """Test that _ensure_initialized can be called multiple times safely."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            first_config = BaseApiTest._config
                            
                            # Initialize again
                            await test_instance._ensure_initialized()
                            second_config = BaseApiTest._config
        
        # Should be the same instance
        assert first_config is second_config


class TestAuthenticatedRequest:
    """Test authenticated_request method."""

    @pytest.mark.asyncio
    async def test_authenticated_request_creates_context(self, mock_config, mock_auth_service, mock_template_service, mock_playwright):
        """Test that authenticated_request creates an API request context with auth."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            with patch('rest_api_testing.base_api_test.async_playwright') as mock_pw:
                                mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_playwright)
                                mock_pw.return_value.__aexit__ = AsyncMock(return_value=None)
                                
                                test_instance = BaseApiTest()
                                test_instance._test_playwright = mock_playwright
                                await test_instance._ensure_initialized()
                                
                                result = await test_instance.authenticated_request()
        
        # Should return PlaywrightApiRequest
        assert isinstance(result, PlaywrightApiRequest)
        
        # Verify context was created with auth header
        mock_playwright.request.new_context.assert_called_once()
        call_kwargs = mock_playwright.request.new_context.call_args.kwargs
        assert "Authorization" in call_kwargs.get("extra_http_headers", {})
        assert call_kwargs["extra_http_headers"]["Authorization"].startswith("Bearer ")

    @pytest.mark.asyncio
    async def test_authenticated_request_includes_base_url(self, mock_config, mock_auth_service, mock_template_service, mock_playwright):
        """Test that authenticated_request uses base URL."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            test_instance._test_playwright = mock_playwright
                            await test_instance._ensure_initialized()
                            
                            await test_instance.authenticated_request()
        
        # Verify base URL is set
        call_kwargs = mock_playwright.request.new_context.call_args.kwargs
        assert call_kwargs["base_url"] == "https://api.example.com"

    @pytest.mark.asyncio
    async def test_authenticated_request_includes_scopes(self, mock_config, mock_auth_service, mock_template_service, mock_playwright):
        """Test that authenticated_request passes scopes to auth service."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            test_instance._test_playwright = mock_playwright
                            test_instance._scopes = ["scope1", "scope2"]
                            test_instance._bypass_cache = False
                            await test_instance._ensure_initialized()
                            
                            await test_instance.authenticated_request()
        
        # Verify scopes were passed to auth service
        mock_auth_service.get_access_token.assert_called_once_with(
            scopes=["scope1", "scope2"],
            bypass_cache=False
        )


class TestUnauthenticatedRequest:
    """Test unauthenticated_request method."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_no_auth_header(self, mock_config, mock_auth_service, mock_template_service, mock_playwright):
        """Test that unauthenticated_request creates context without auth."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            test_instance._test_playwright = mock_playwright
                            await test_instance._ensure_initialized()
                            
                            result = await test_instance.unauthenticated_request()
        
        # Should return PlaywrightApiRequest
        assert isinstance(result, PlaywrightApiRequest)
        
        # Verify context was created without Authorization header
        mock_playwright.request.new_context.assert_called_once()
        call_kwargs = mock_playwright.request.new_context.call_args.kwargs
        headers = call_kwargs.get("extra_http_headers", {})
        assert "Authorization" not in headers

    @pytest.mark.asyncio
    async def test_unauthenticated_request_has_content_type(self, mock_config, mock_auth_service, mock_template_service, mock_playwright):
        """Test that unauthenticated_request includes Content-Type header."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            test_instance._test_playwright = mock_playwright
                            await test_instance._ensure_initialized()
                            
                            await test_instance.unauthenticated_request()
        
        call_kwargs = mock_playwright.request.new_context.call_args.kwargs
        headers = call_kwargs.get("extra_http_headers", {})
        assert headers.get("Content-Type") == "application/json"


class TestTemplateRendering:
    """Test template rendering methods."""

    @pytest.mark.asyncio
    async def test_render_template(self, mock_config, mock_auth_service, mock_template_service):
        """Test render_template method."""
        context = {"name": "John"}
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            result = test_instance.render_template("user.json.j2", context)
        
        # Verify template service was called
        mock_template_service.render.assert_called_once_with("user.json.j2", context)
        assert result == '{"rendered": "data"}'

    @pytest.mark.asyncio
    async def test_render_template_with_csv(self, mock_config, mock_auth_service, mock_template_service):
        """Test render_template_with_csv method."""
        additional_context = {"extra": "value"}
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            result = test_instance.render_template_with_csv(
                                "user.json.j2",
                                "user-data.csv",
                                row_index=1,
                                additional_context=additional_context
                            )
        
        # Verify template service was called
        mock_template_service.render_with_csv.assert_called_once_with(
            "user.json.j2",
            "user-data.csv",
            1,
            additional_context
        )


class TestCSVLoading:
    """Test CSV loading methods."""

    @pytest.mark.asyncio
    async def test_load_csv_as_dict(self, mock_config, mock_auth_service, mock_template_service):
        """Test load_csv_as_dict method."""
        expected_row = {"firstName": "John", "lastName": "Doe", "email": "john@example.com"}
        mock_template_service.load_csv_as_dict = MagicMock(return_value=expected_row)
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            result = test_instance.load_csv_as_dict("user-data.csv", row_index=0)
        
        mock_template_service.load_csv_as_dict.assert_called_once_with("user-data.csv", 0)
        assert result == expected_row

    @pytest.mark.asyncio
    async def test_load_csv_as_list(self, mock_config, mock_auth_service, mock_template_service):
        """Test load_csv_as_list method."""
        expected_rows = [
            {"firstName": "John", "lastName": "Doe"},
            {"firstName": "Jane", "lastName": "Smith"}
        ]
        mock_template_service.load_csv_as_list = MagicMock(return_value=expected_rows)
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            result = test_instance.load_csv_as_list("user-data.csv")
        
        mock_template_service.load_csv_as_list.assert_called_once_with("user-data.csv")
        assert result == expected_rows


class TestScopeExtraction:
    """Test OAuth scope extraction."""

    @pytest.mark.asyncio
    async def test_extract_scopes_from_class(self, mock_config, mock_auth_service, mock_template_service):
        """Test extracting scopes from class decorator."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            # Create a test class with scopes
                            class TestWithScopes(BaseApiTest):
                                _oauth_scopes = ["scope1", "scope2"]
                            
                            test_instance = TestWithScopes()
                            scopes = test_instance._extract_scopes()
        
        assert scopes == ["scope1", "scope2"]

    @pytest.mark.asyncio
    async def test_extract_scopes_from_method(self, mock_config, mock_auth_service, mock_template_service):
        """Test extracting scopes from method decorator."""
        def mock_method():
            pass
        
        mock_method._oauth_scopes = ["method_scope1", "method_scope2"]
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            scopes = test_instance._extract_scopes(method=mock_method)
        
        assert scopes == ["method_scope1", "method_scope2"]

    @pytest.mark.asyncio
    async def test_extract_scopes_none(self, mock_config, mock_auth_service, mock_template_service):
        """Test extracting scopes when none are set."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            scopes = test_instance._extract_scopes()
        
        assert scopes is None


class TestBypassCacheExtraction:
    """Test token cache bypass flag extraction."""

    @pytest.mark.asyncio
    async def test_extract_bypass_cache_from_class(self, mock_config, mock_auth_service, mock_template_service):
        """Test extracting bypass cache flag from class decorator."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            class TestWithBypassCache(BaseApiTest):
                                _bypass_token_cache = True
                            
                            test_instance = TestWithBypassCache()
                            bypass = test_instance._extract_bypass_cache()
        
        assert bypass is True

    @pytest.mark.asyncio
    async def test_extract_bypass_cache_false(self, mock_config, mock_auth_service, mock_template_service):
        """Test extracting bypass cache flag when not set."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            bypass = test_instance._extract_bypass_cache()
        
        assert bypass is False


class TestPropertyAccessors:
    """Test property accessors."""

    @pytest.mark.asyncio
    async def test_config_property(self, mock_config, mock_auth_service, mock_template_service):
        """Test accessing config property."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            config = test_instance.config
        
        assert config is mock_config

    @pytest.mark.asyncio
    async def test_auth_service_property(self, mock_config, mock_auth_service, mock_template_service):
        """Test accessing auth_service property."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            auth = test_instance.auth_service
        
        assert auth is mock_auth_service

    @pytest.mark.asyncio
    async def test_template_service_property(self, mock_config, mock_auth_service, mock_template_service):
        """Test accessing template_service property."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            template = test_instance.template_service
        
        assert template is mock_template_service

    @pytest.mark.asyncio
    async def test_playwright_property(self, mock_config, mock_auth_service, mock_template_service, mock_playwright):
        """Test accessing playwright property."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            test_instance._test_playwright = mock_playwright
                            await test_instance._ensure_initialized()
                            
                            pw = test_instance.playwright
        
        assert pw is mock_playwright

    def test_playwright_property_not_initialized(self, mock_config, mock_auth_service, mock_template_service):
        """Test accessing playwright property when not initialized."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            
                            with pytest.raises(RuntimeError):
                                _ = test_instance.playwright

    @pytest.mark.asyncio
    async def test_config_property_not_initialized(self):
        """Test accessing config property when not initialized."""
        test_instance = BaseApiTest()
        
        with pytest.raises(RuntimeError):
            _ = test_instance.config


class TestCustomizeApiRequestContext:
    """Test customizing API request context."""

    @pytest.mark.asyncio
    async def test_customize_api_request_context_default_noop(self, mock_config, mock_auth_service, mock_template_service):
        """Test that default customize method is no-op."""
        mock_context = MagicMock(spec=APIRequestContext)
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    test_instance = BaseApiTest()
                    # Should not raise error
                    test_instance.customize_api_request_context(mock_context)

    @pytest.mark.asyncio
    async def test_customize_api_request_context_override(self, mock_config, mock_auth_service, mock_template_service):
        """Test that customize method can be overridden."""
        
        class CustomTestClass(BaseApiTest):
            customized = False
            
            def customize_api_request_context(self, context):
                self.customized = True
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    test_instance = CustomTestClass()
                    mock_context = MagicMock(spec=APIRequestContext)
                    test_instance.customize_api_request_context(mock_context)
        
        assert test_instance.customized is True
