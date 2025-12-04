"""Base API test class for REST API testing."""

import asyncio
import logging
import pytest
from typing import Optional, List, Dict
from playwright.async_api import Playwright, APIRequestContext, async_playwright
from rest_api_testing.config import get_config
from rest_api_testing.auth import AuthenticationService
from rest_api_testing.template import TemplateService
from rest_api_testing.playwright_api import PlaywrightApiRequest
from rest_api_testing.logging_setup import setup_logging, log_config

logger = logging.getLogger(__name__)

class BaseApiTest:
    """Base test class that sets up Playwright API testing configuration and authentication."""

    _config = None
    _auth_service = None
    _template_service = None
    _playwright_instances: Dict[type, Playwright] = {}  # Per-class Playwright instances
    _initialized = False
    _scopes = None
    _bypass_cache = False
    _unauthenticated_api_request_context = None
    _api_request_context = None
    _playwright_lock = None

    @classmethod
    async def _ensure_initialized(cls):
        """Ensure static resources are initialized (lazy initialization)."""
        # Always initialize on BaseApiTest, not the subclass
        base_cls = BaseApiTest
        if not base_cls._initialized:
            # Initialize lock if needed (can't be done at class definition time)
            if base_cls._playwright_lock is None:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                base_cls._playwright_lock = asyncio.Lock()
            
            async with base_cls._playwright_lock:
                if not base_cls._initialized:
                    base_cls._config = get_config()
                    # Set up logging with configuration
                    setup_logging(
                        log_directory=base_cls._config.log_directory,
                        log_level=base_cls._config.log_level,
                        log_to_console=True,
                    )
                    # Log configuration at startup
                    log_config(base_cls._config)
                    base_cls._auth_service = AuthenticationService.get_instance()
                    base_cls._template_service = TemplateService.get_instance()
                    # Note: Playwright instances are now created per test class, not globally

                    base_cls._initialized = True
                    logger.info(
                        "Test suite initialized. API Base URL: %s",
                        base_cls._config.api_base_url,
                    )
                    logger.debug("Class variables set: _auth_service=%s, _config=%s, _initialized=%s", 
                                base_cls._auth_service, base_cls._config, base_cls._initialized)
                    # Double-check that variables are actually set
                    assert base_cls._auth_service is not None, "auth_service should not be None"
                    assert base_cls._config is not None, "config should not be None"
                    logger.debug("Verification passed: base_cls=%s, base_cls._auth_service=%s", base_cls, base_cls._auth_service)
            
    @pytest.fixture(autouse=True, scope="function")
    async def _test_setup_teardown(self, request):
        """Setup and teardown fixture called before/after each test (pytest fixture)."""
        # Ensure static resources are initialized
        await self._ensure_initialized()
        
        # Create a FRESH Playwright instance for each test to avoid context corruption
        test_class = self.__class__
        logger.debug("Creating fresh Playwright instance for test: %s.%s", 
                    test_class.__name__, request.function.__name__ if request.function else "unknown")
        # Store per-test instance temporarily
        self._test_playwright = await async_playwright().start()
        logger.info(
            "Test Playwright initialized for %s.%s. API Base URL: %s",
            test_class.__name__,
            request.function.__name__ if request.function else "unknown",
            BaseApiTest._config.api_base_url,
        )
        
        # Debug: Verify initialization
        logger.debug("After _ensure_initialized: self.__class__=%s, BaseApiTest=%s", 
                    self.__class__, BaseApiTest)
        logger.debug("Class vars: BaseApiTest._auth_service=%s, BaseApiTest._config=%s, BaseApiTest._initialized=%s", 
                    BaseApiTest._auth_service, BaseApiTest._config, BaseApiTest._initialized)
        logger.debug("Instance class vars: self.__class__._auth_service=%s, self.__class__._config=%s", 
                    self.__class__._auth_service, self.__class__._config)
        
        test_name = request.function.__name__ if request.function else "unknown"
        logger.info("=" * 80)
        logger.info("Starting test: %s.%s", self.__class__.__name__, test_name)
        logger.info("=" * 80)

        # Get OAuth scopes from test method or class (if using decorators)
        method = request.function if hasattr(request, 'function') else None
        self._scopes = self._extract_scopes(method=method)
        if self._scopes:
            logger.info("Using OAuth scopes: %s", ", ".join(self._scopes))
        else:
            logger.debug("No OAuth scopes specified for this test")

        # Check if token cache should be bypassed
        self._bypass_cache = self._extract_bypass_cache(method=method)
        if self._bypass_cache:
            logger.info("Token cache will be bypassed for this test")

        logger.info("Test setup completed for: %s.%s", self.__class__.__name__, test_name)
        
        yield
        
        # Teardown - Clean up per-test Playwright instance
        test_name = request.function.__name__ if request.function else "unknown"
        logger.info("=" * 80)
        logger.info("Completing test: %s.%s", self.__class__.__name__, test_name)
        logger.info("=" * 80)
        # Clear references but don't dispose contexts - they'll be cleaned with Playwright
        self._api_request_context = None
        self._unauthenticated_api_request_context = None
        # Stop the per-test Playwright instance
        if hasattr(self, '_test_playwright') and self._test_playwright:
            await self._test_playwright.stop()
            self._test_playwright = None
            logger.debug("Stopped Playwright instance for test")

    def customize_api_request_context(
        self, context: APIRequestContext
    ) -> None:
        """
        Override this method to customize API request context for specific test classes.

        Args:
            context: The API request context to customize
        """
        # Default implementation - override in subclasses if needed
        pass

    async def authenticated_request(self) -> PlaywrightApiRequest:
        """
        Get a fluent API request builder with authentication.

        Returns:
            PlaywrightApiRequest builder for authenticated API calls
        """
        # Get JWT token for authentication with scopes
        access_token = await self.auth_service.get_access_token(
            scopes=self._scopes, bypass_cache=self._bypass_cache
        )

        # Create API request context with base configuration
        self._api_request_context = await self.playwright.request.new_context(
            base_url=self.config.api_base_url,
            extra_http_headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=self.config.test_timeout,
            ignore_https_errors=True,  # Use only in test environments
        )

        # Allow customization
        self.customize_api_request_context(self._api_request_context)

        # Return a context object that can be used to make API requests
        return PlaywrightApiRequest(self._api_request_context)

    async def unauthenticated_request(self) -> PlaywrightApiRequest:
        """
        Get a fluent API request builder without authentication.

        Creates an unauthenticated API request context that does not include
        the Authorization header. Useful for testing unauthorized access scenarios.

        Returns:
            PlaywrightApiRequest builder for unauthenticated API calls
        """
        # Create API request context without authentication
        self._unauthenticated_api_request_context = (
            await self.playwright.request.new_context(
                base_url=self.config.api_base_url,
                extra_http_headers={"Content-Type": "application/json"},
                timeout=self.config.test_timeout,
                ignore_https_errors=True,  # Use only in test environments
            )
        )

        # Allow customization
        self.customize_api_request_context(self._unauthenticated_api_request_context)

        # Return a context object that can be used to make API requests
        return PlaywrightApiRequest(self._unauthenticated_api_request_context)

    def render_template(
        self, template_path: str, context: Optional[dict] = None
    ) -> str:
        """
        Render a Jinja2 template with the provided context variables.

        Args:
            template_path: Path to the template file (e.g., "templates/user-create.json.j2")
            context: Dictionary of variables to use in the template

        Returns:
            Rendered template as a string (typically JSON)
        """
        return self.template_service.render(template_path, context or {})

    def render_template_with_csv(
        self,
        template_path: str,
        csv_file_path: str,
        row_index: int = 0,
        additional_context: Optional[dict] = None,
    ) -> str:
        """
        Render a Jinja2 template using data loaded from a CSV file.

        Args:
            template_path: Path to the template file
            csv_file_path: Path to the CSV data file
            row_index: Zero-based index of the data row to use
            additional_context: Optional dictionary of additional variables to merge with CSV data

        Returns:
            Rendered template as a string
        """
        return self.template_service.render_with_csv(
            template_path, csv_file_path, row_index, additional_context
        )

    def load_csv_as_dict(
        self, csv_file_path: str, row_index: int = 0
    ) -> dict:
        """
        Load a CSV file and parse it into a dictionary.

        Args:
            csv_file_path: Path to the CSV file (e.g., "templates/user-data.csv")
            row_index: Zero-based index of the data row to parse (0 = first data row after header)

        Returns:
            Dictionary with column headers as keys and row values as values
        """
        return self.template_service.load_csv_as_dict(csv_file_path, row_index)

    def load_csv_as_list(self, csv_file_path: str) -> List[dict]:
        """
        Load a CSV file and parse all data rows into a list of dictionaries.

        Args:
            csv_file_path: Path to the CSV file (e.g., "templates/user-data.csv")

        Returns:
            List of dictionaries, where each dictionary represents a data row
        """
        return self.template_service.load_csv_as_list(csv_file_path)

    def _extract_scopes(self, method=None) -> Optional[List[str]]:
        """
        Extract OAuth scopes from test method or class using @oauth_scopes decorator.

        Checks for scopes in this order:
        1. Method-level @oauth_scopes decorator
        2. Class-level @oauth_scopes decorator

        Args:
            method: The test method (bound method from pytest)

        Returns:
            List of OAuth scopes, or None if not specified
        """
        # Check method-level scopes first (highest priority)
        if method is not None:
            # Get the underlying function from the bound method
            func = method.__func__ if hasattr(method, "__func__") else method
            
            # Check if the function has the _oauth_scopes attribute
            if hasattr(func, "_oauth_scopes"):
                scopes = getattr(func, "_oauth_scopes")
                if scopes:
                    logger.debug("Found method-level OAuth scopes: %s", scopes)
                    return scopes
        
        # Check class-level scopes
        if hasattr(self.__class__, "_oauth_scopes"):
            scopes = getattr(self.__class__, "_oauth_scopes")
            if scopes:
                logger.debug("Found class-level OAuth scopes: %s", scopes)
                return scopes
        
        return None

    def _extract_bypass_cache(self, method=None) -> bool:
        """
        Extract bypass_token_cache flag from test method or class using @bypass_token_cache decorator.

        Checks for bypass flag in this order:
        1. Method-level @bypass_token_cache decorator
        2. Class-level @bypass_token_cache decorator

        Args:
            method: The test method (bound method from pytest)

        Returns:
            True if token cache should be bypassed, False otherwise
        """
        # Check method-level bypass flag first (highest priority)
        if method is not None:
            # Get the underlying function from the bound method
            func = method.__func__ if hasattr(method, "__func__") else method
            
            # Check if the function has the _bypass_token_cache attribute
            if hasattr(func, "_bypass_token_cache"):
                bypass = getattr(func, "_bypass_token_cache")
                if bypass:
                    logger.debug("Found method-level bypass_token_cache flag")
                    return True
        
        # Check class-level bypass flag
        if hasattr(self.__class__, "_bypass_token_cache"):
            bypass = getattr(self.__class__, "_bypass_token_cache")
            if bypass:
                logger.debug("Found class-level bypass_token_cache flag")
                return True
        
        return False

    @property
    def config(self):
        """Get the test configuration."""
        # Access through the base class to ensure we get the shared instance
        cls = BaseApiTest
        if cls._config is None:
            raise RuntimeError(
                "Test configuration not initialized. Ensure _ensure_initialized() has been called."
            )
        return cls._config

    @property
    def auth_service(self):
        """Get the authentication service."""
        # Access through the base class to ensure we get the shared instance
        cls = BaseApiTest
        if cls._auth_service is None:
            raise RuntimeError(
                "Authentication service not initialized. Ensure _ensure_initialized() has been called."
            )
        return cls._auth_service

    @property
    def template_service(self):
        """Get the template service."""
        # Access through the base class to ensure we get the shared instance
        cls = BaseApiTest
        if cls._template_service is None:
            raise RuntimeError(
                "Template service not initialized. Ensure _ensure_initialized() has been called."
            )
        return cls._template_service

    @property
    def playwright(self) -> Playwright:
        """Get the Playwright instance for this test."""
        # Each test gets its own fresh Playwright instance to avoid context corruption
        if not hasattr(self, '_test_playwright') or self._test_playwright is None:
            raise RuntimeError(
                "Playwright instance not initialized for this test. "
                "Ensure the test fixture has been called."
            )
        return self._test_playwright
