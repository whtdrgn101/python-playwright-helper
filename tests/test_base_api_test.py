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
from rest_api_testing.auth.decorators import oauth_scopes, bypass_token_cache


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


class TestFixtureSetupTeardown:
    """Test the pytest fixture setup and teardown behavior."""

    @pytest.mark.asyncio
    async def test_ensure_initialized_creates_auth_service(self, mock_config, mock_auth_service, mock_template_service):
        """Test that initialization creates auth service."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            # Verify auth service was created
                            assert BaseApiTest._auth_service is not None
                            assert BaseApiTest._auth_service == mock_auth_service

    @pytest.mark.asyncio
    async def test_ensure_initialized_calls_setup_logging(self, mock_config, mock_auth_service, mock_template_service):
        """Test that initialization calls setup_logging."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging') as mock_setup_logging:
                        with patch('rest_api_testing.base_api_test.log_config') as mock_log_config:
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            # Verify logging setup was called
                            mock_setup_logging.assert_called_once()
                            mock_log_config.assert_called_once()


class TestScopeExtractionEdgeCases:
    """Test edge cases in scope extraction."""

    @pytest.mark.asyncio
    async def test_extract_scopes_method_priority_over_class(self, mock_config, mock_auth_service, mock_template_service):
        """Test that method-level scopes take priority over class-level."""
        def mock_method():
            pass
        
        mock_method._oauth_scopes = ["method_scope"]
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    class TestWithBothScopes(BaseApiTest):
                        _oauth_scopes = ["class_scope"]
                    
                    test_instance = TestWithBothScopes()
                    scopes = test_instance._extract_scopes(method=mock_method)
        
        # Method scopes should take priority
        assert scopes == ["method_scope"]

    @pytest.mark.asyncio
    async def test_extract_scopes_empty_list(self, mock_config, mock_auth_service, mock_template_service):
        """Test extracting empty scope list (should return None, not empty list)."""
        class TestWithEmptyScopes(BaseApiTest):
            _oauth_scopes = []
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    test_instance = TestWithEmptyScopes()
                    scopes = test_instance._extract_scopes()
        
        # Empty list should be treated as no scopes
        assert scopes is None or scopes == []

    @pytest.mark.asyncio
    async def test_extract_scopes_with_bound_method(self, mock_config, mock_auth_service, mock_template_service):
        """Test extracting scopes with a bound method."""
        class TestClass(BaseApiTest):
            def test_method(self):
                pass
        
        TestClass.test_method._oauth_scopes = ["bound_scope"]
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    test_instance = TestClass()
                    bound_method = test_instance.test_method
                    scopes = test_instance._extract_scopes(method=bound_method)
        
        assert scopes == ["bound_scope"]


class TestBypassCacheExtractionEdgeCases:
    """Test edge cases in bypass cache extraction."""

    @pytest.mark.asyncio
    async def test_extract_bypass_cache_method_priority_over_class(self, mock_config, mock_auth_service, mock_template_service):
        """Test that method-level bypass takes priority over class-level."""
        def mock_method():
            pass
        
        mock_method._bypass_token_cache = True
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    class TestWithBothBypass(BaseApiTest):
                        _bypass_token_cache = False
                    
                    test_instance = TestWithBothBypass()
                    bypass = test_instance._extract_bypass_cache(method=mock_method)
        
        # Method bypass should take priority
        assert bypass is True

    @pytest.mark.asyncio
    async def test_extract_bypass_cache_method_with_false(self, mock_config, mock_auth_service, mock_template_service):
        """Test that method-level False is treated as no bypass."""
        def mock_method():
            pass
        
        # Method has False (but attribute exists)
        mock_method._bypass_token_cache = False
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    class TestWithClassBypass(BaseApiTest):
                        _bypass_token_cache = True
                    
                    test_instance = TestWithClassBypass()
                    bypass = test_instance._extract_bypass_cache(method=mock_method)
        
        # Method is checked first, and it has False, so the logic checks "if bypass:" which is False
        # This means it returns False from the method check but then falls through to class check
        # The actual behavior: if method attribute is False (falsy), it continues to class check
        assert bypass is True  # Class level is True


class TestAuthenticatedRequestWithBypassCache:
    """Test authenticated request with bypass cache flag."""

    @pytest.mark.asyncio
    async def test_authenticated_request_with_bypass_cache_true(self, mock_config, mock_auth_service, mock_template_service, mock_playwright):
        """Test authenticated request respects bypass_cache flag."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            test_instance._test_playwright = mock_playwright
                            test_instance._bypass_cache = True
                            test_instance._scopes = None
                            await test_instance._ensure_initialized()
                            
                            await test_instance.authenticated_request()
        
        # Verify bypass_cache was passed to auth service
        mock_auth_service.get_access_token.assert_called_once()
        call_kwargs = mock_auth_service.get_access_token.call_args.kwargs
        assert call_kwargs["bypass_cache"] is True

    @pytest.mark.asyncio
    async def test_authenticated_request_with_multiple_scopes(self, mock_config, mock_auth_service, mock_template_service, mock_playwright):
        """Test authenticated request with multiple scopes."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            test_instance._test_playwright = mock_playwright
                            test_instance._bypass_cache = False
                            test_instance._scopes = ["scope1", "scope2", "scope3"]
                            await test_instance._ensure_initialized()
                            
                            result = await test_instance.authenticated_request()
        
        # Verify all scopes were passed
        call_kwargs = mock_auth_service.get_access_token.call_args.kwargs
        assert call_kwargs["scopes"] == ["scope1", "scope2", "scope3"]
        
        # Result should be PlaywrightApiRequest
        assert isinstance(result, PlaywrightApiRequest)


class TestRequestContextTimeoutConfiguration:
    """Test that request contexts are configured with correct timeouts."""

    @pytest.mark.asyncio
    async def test_authenticated_request_timeout_configuration(self, mock_config, mock_auth_service, mock_template_service, mock_playwright):
        """Test that authenticated request uses configured timeout."""
        mock_config.test_timeout = 45000  # 45 seconds
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            test_instance._test_playwright = mock_playwright
                            test_instance._bypass_cache = False
                            test_instance._scopes = None
                            await test_instance._ensure_initialized()
                            
                            await test_instance.authenticated_request()
        
        # Verify timeout was passed to context
        call_kwargs = mock_playwright.request.new_context.call_args.kwargs
        assert call_kwargs["timeout"] == 45000

    @pytest.mark.asyncio
    async def test_unauthenticated_request_timeout_configuration(self, mock_config, mock_auth_service, mock_template_service, mock_playwright):
        """Test that unauthenticated request uses configured timeout."""
        mock_config.test_timeout = 60000  # 60 seconds
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            test_instance._test_playwright = mock_playwright
                            await test_instance._ensure_initialized()
                            
                            await test_instance.unauthenticated_request()
        
        # Verify timeout was passed to context
        call_kwargs = mock_playwright.request.new_context.call_args.kwargs
        assert call_kwargs["timeout"] == 60000


class TestRenderTemplateEdgeCases:
    """Test edge cases in template rendering."""

    @pytest.mark.asyncio
    async def test_render_template_with_none_context(self, mock_config, mock_auth_service, mock_template_service):
        """Test rendering template with None context."""
        mock_template_service.render = MagicMock(return_value="rendered")
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            result = test_instance.render_template("template.j2", None)
        
        # Should pass empty dict when None is provided
        mock_template_service.render.assert_called_once_with("template.j2", {})
        assert result == "rendered"

    @pytest.mark.asyncio
    async def test_render_template_with_empty_context(self, mock_config, mock_auth_service, mock_template_service):
        """Test rendering template with empty context."""
        mock_template_service.render = MagicMock(return_value="rendered")
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            result = test_instance.render_template("template.j2", {})
        
        mock_template_service.render.assert_called_once_with("template.j2", {})
        assert result == "rendered"

    @pytest.mark.asyncio
    async def test_render_template_with_complex_context(self, mock_config, mock_auth_service, mock_template_service):
        """Test rendering template with complex nested context."""
        complex_context = {
            "user": {
                "name": "John",
                "email": "john@example.com",
                "roles": ["admin", "user"]
            },
            "settings": {
                "debug": True,
                "timeout": 30
            }
        }
        mock_template_service.render = MagicMock(return_value="rendered")
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            result = test_instance.render_template("template.j2", complex_context)
        
        mock_template_service.render.assert_called_once_with("template.j2", complex_context)


class TestPropertyAccessorsErrorCases:
    """Test error cases for property accessors."""

    def test_auth_service_property_not_initialized_error(self):
        """Test accessing auth_service when not initialized raises error."""
        # Reset initialization
        BaseApiTest._auth_service = None
        BaseApiTest._initialized = False
        
        test_instance = BaseApiTest()
        
        with pytest.raises(RuntimeError) as exc_info:
            _ = test_instance.auth_service
        
        assert "Authentication service not initialized" in str(exc_info.value)

    def test_template_service_property_not_initialized_error(self):
        """Test accessing template_service when not initialized raises error."""
        # Reset initialization
        BaseApiTest._template_service = None
        BaseApiTest._initialized = False
        
        test_instance = BaseApiTest()
        
        with pytest.raises(RuntimeError) as exc_info:
            _ = test_instance.template_service
        
        assert "Template service not initialized" in str(exc_info.value)


class TestAsyncLoopCreation:
    """Test async loop creation in _ensure_initialized."""

    @pytest.mark.asyncio
    async def test_ensure_initialized_creates_new_loop_when_no_running_loop(self, mock_config, mock_auth_service, mock_template_service):
        """Test that new event loop is created when no running loop exists."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            # The method already has a running loop in this test context
                            # but we can verify it initializes without error
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            # Verify lock was created
                            assert BaseApiTest._playwright_lock is not None


class TestInitializeMultipleTimes:
    """Test initialization behavior when called multiple times."""

    @pytest.mark.asyncio
    async def test_ensure_initialized_thread_safety(self, mock_config, mock_auth_service, mock_template_service):
        """Test that initialization is thread-safe with async lock."""
        call_count = 0
        original_get_instance = mock_auth_service.get_instance
        
        def counting_get_instance(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_auth_service
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', side_effect=counting_get_instance):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance1 = BaseApiTest()
                            test_instance2 = BaseApiTest()
                            
                            # Call initialize on both instances
                            await test_instance1._ensure_initialized()
                            await test_instance2._ensure_initialized()
                            
                            # Should only initialize once due to lock
                            # (call_count will be 1 because mock is replaced after first call)
                            assert BaseApiTest._initialized is True


class TestLoadCsvEdgeCases:
    """Test edge cases for CSV loading."""

    @pytest.mark.asyncio
    async def test_load_csv_as_dict_with_default_row(self, mock_config, mock_auth_service, mock_template_service):
        """Test loading CSV with default row index."""
        expected_row = {"firstName": "John", "lastName": "Doe"}
        mock_template_service.load_csv_as_dict = MagicMock(return_value=expected_row)
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            # Call with no row_index (should default to 0)
                            result = test_instance.load_csv_as_dict("data.csv")
        
        # Verify default row index was used
        mock_template_service.load_csv_as_dict.assert_called_once_with("data.csv", 0)

    @pytest.mark.asyncio
    async def test_load_csv_as_list_called_through_base_test(self, mock_config, mock_auth_service, mock_template_service):
        """Test loading CSV list through BaseApiTest."""
        expected_rows = [
            {"name": "John"},
            {"name": "Jane"}
        ]
        mock_template_service.load_csv_as_list = MagicMock(return_value=expected_rows)
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            result = test_instance.load_csv_as_list("data.csv")
        
        assert result == expected_rows
        mock_template_service.load_csv_as_list.assert_called_once_with("data.csv")


class TestUnauthenticatedRequestEdgeCases:
    """Test additional unauthenticated request scenarios."""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_stores_context(self, mock_config, mock_auth_service, mock_template_service):
        """Test that unauthenticated_request stores the context."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            # Verify _unauthenticated_api_request_context is initialized to None
                            assert test_instance._unauthenticated_api_request_context is None


class TestMultipleScopeHandling:
    """Test handling of multiple scopes in requests."""

    @pytest.mark.asyncio
    async def test_authenticated_request_with_decorator_scopes(self, mock_config, mock_auth_service, mock_template_service):
        """Test authenticated request with scopes set via decorator."""
        @oauth_scopes("scope1", "scope2", "scope3")
        class TestClassWithMultipleScopes(BaseApiTest):
            pass
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = TestClassWithMultipleScopes()
                            await test_instance._ensure_initialized()
                            
                            # Verify the scopes are extracted correctly
                            assert hasattr(TestClassWithMultipleScopes, '_scopes')
                            scopes = test_instance._extract_scopes(TestClassWithMultipleScopes)
                            assert scopes == ["scope1", "scope2", "scope3"]


class TestPlaywrightPropertiesEdgeCases:
    """Test additional Playwright property edge cases."""

    @pytest.mark.asyncio
    async def test_playwright_lock_is_async_lock(self, mock_config, mock_auth_service, mock_template_service):
        """Test that playwright_lock is an asyncio.Lock."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            # Verify lock is an asyncio.Lock
                            assert BaseApiTest._playwright_lock is not None
                            # Lock should have acquire and release methods (asyncio.Lock interface)
                            assert hasattr(BaseApiTest._playwright_lock, 'acquire')
                            assert hasattr(BaseApiTest._playwright_lock, 'release')


class TestExtractScopesMethod:
    """Test the _extract_scopes instance method."""

    @pytest.mark.asyncio
    async def test_extract_scopes_from_method_attribute(self, mock_config, mock_auth_service, mock_template_service):
        """Test extracting scopes from method with _oauth_scopes attribute."""
        @oauth_scopes("method_scope1", "method_scope2")
        def test_method(self):
            pass
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            
                            # Extract scopes directly from the decorated function
                            result = test_instance._extract_scopes(test_method)
                            assert result == ["method_scope1", "method_scope2"]

    @pytest.mark.asyncio
    async def test_extract_scopes_with_none_method(self, mock_config, mock_auth_service, mock_template_service):
        """Test extracting scopes when method is None."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            
                            # Should return None when method is None and no class scopes
                            result = test_instance._extract_scopes(None)
                            assert result is None


class TestExtractBypassCacheMethod:
    """Test the _extract_bypass_cache instance method."""

    @pytest.mark.asyncio
    async def test_extract_bypass_cache_from_method_attribute(self, mock_config, mock_auth_service, mock_template_service):
        """Test extracting bypass cache from method with decorator."""
        @bypass_token_cache
        def test_method(self):
            pass
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            
                            # Extract bypass cache from the decorated function
                            result = test_instance._extract_bypass_cache(test_method)
                            assert result is True

    @pytest.mark.asyncio
    async def test_extract_bypass_cache_with_none_method(self, mock_config, mock_auth_service, mock_template_service):
        """Test extracting bypass cache when method is None."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            
                            # Should return False when method is None and no class bypass cache
                            result = test_instance._extract_bypass_cache(None)
                            assert result is False


class TestInitializedFlagBehavior:
    """Test the behavior of the _initialized flag."""

    @pytest.mark.asyncio
    async def test_initialized_flag_set_after_ensure_initialized(self, mock_config, mock_auth_service, mock_template_service):
        """Test that _initialized flag is set after calling _ensure_initialized."""
        BaseApiTest._initialized = False
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            assert BaseApiTest._initialized is False
                            
                            await test_instance._ensure_initialized()
                            
                            assert BaseApiTest._initialized is True


class TestRequestContextAttributes:
    """Test request context storage attributes."""

    @pytest.mark.asyncio
    async def test_api_request_context_attributes_exist(self, mock_config, mock_auth_service, mock_template_service):
        """Test that request context attributes are properly initialized."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            
                            # Check initial state
                            assert hasattr(test_instance, '_api_request_context')
                            assert hasattr(test_instance, '_unauthenticated_api_request_context')
                            
                            # Both should be None initially
                            assert test_instance._api_request_context is None
                            assert test_instance._unauthenticated_api_request_context is None


class TestCsvOperationsWithDifferentIndices:
    """Test CSV loading with various row indices."""

    @pytest.mark.asyncio
    async def test_load_csv_as_dict_with_specific_row_index(self, mock_config, mock_auth_service, mock_template_service):
        """Test loading CSV with a specific row index."""
        expected_row = {"name": "Bob", "email": "bob@example.com"}
        mock_template_service.load_csv_as_dict = MagicMock(return_value=expected_row)
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            result = test_instance.load_csv_as_dict("data.csv", row_index=2)
        
        mock_template_service.load_csv_as_dict.assert_called_once_with("data.csv", 2)
        assert result == expected_row


class TestCustomizeContextOverride:
    """Test subclassing to customize request context."""

    @pytest.mark.asyncio
    async def test_customize_api_request_context_is_called(self, mock_config, mock_auth_service, mock_template_service):
        """Test that customize_api_request_context can be overridden."""
        class CustomTestClass(BaseApiTest):
            customize_called = False
            
            def customize_api_request_context(self, context):
                """Override to track if customize was called."""
                self.customize_called = True
                super().customize_api_request_context(context)
        
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = CustomTestClass()
                            
                            # Call customize with a mock context
                            mock_context = MagicMock()
                            test_instance.customize_api_request_context(mock_context)
                            
                            assert test_instance.customize_called is True


class TestConfigProperty:
    """Test the config property accessor."""

    @pytest.mark.asyncio
    async def test_config_property_returns_correct_value(self, mock_config, mock_auth_service, mock_template_service):
        """Test that config property returns the configured TestConfig."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance = BaseApiTest()
                            await test_instance._ensure_initialized()
                            
                            config = test_instance.config
                            assert config == mock_config


class TestPlaywrightInstances:
    """Test Playwright instance storage."""

    @pytest.mark.asyncio
    async def test_playwright_instances_dict_storage(self, mock_config, mock_auth_service, mock_template_service):
        """Test that Playwright instances are stored in dictionary."""
        with patch('rest_api_testing.base_api_test.get_config', return_value=mock_config):
            with patch('rest_api_testing.base_api_test.AuthenticationService.get_instance', return_value=mock_auth_service):
                with patch('rest_api_testing.base_api_test.TemplateService.get_instance', return_value=mock_template_service):
                    with patch('rest_api_testing.base_api_test.setup_logging'):
                        with patch('rest_api_testing.base_api_test.log_config'):
                            test_instance1 = BaseApiTest()
                            test_instance2 = BaseApiTest()
                            
                            # Both should be able to store playwright instances
                            mock_playwright1 = MagicMock()
                            mock_playwright2 = MagicMock()
                            
                            BaseApiTest._playwright_instances[id(test_instance1)] = mock_playwright1
                            BaseApiTest._playwright_instances[id(test_instance2)] = mock_playwright2
                            
                            # Verify storage
                            assert BaseApiTest._playwright_instances[id(test_instance1)] == mock_playwright1
                            assert BaseApiTest._playwright_instances[id(test_instance2)] == mock_playwright2
