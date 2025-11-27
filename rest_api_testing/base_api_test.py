"""Base API test class for REST API testing."""

import logging
from typing import Optional, List
from playwright.sync_api import Playwright, APIRequestContext, sync_playwright
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
    _playwright: Optional[Playwright] = None
    _initialized = False
    _scopes = None
    _bypass_cache = False

    @classmethod
    def _ensure_initialized(cls):
        """Ensure static resources are initialized (lazy initialization)."""
        if not cls._initialized:
            import asyncio
            import threading
            
            cls._config = get_config()
            # Set up logging with configuration
            setup_logging(
                log_directory=cls._config.log_directory,
                log_level=cls._config.log_level,
                log_to_console=True,
            )
            # Log configuration at startup
            log_config(cls._config)
            cls._auth_service = AuthenticationService.get_instance()
            cls._template_service = TemplateService.get_instance()
            
            # Check if there's a running event loop and handle it
            try:
                loop = asyncio.get_running_loop()
                # If there's a running loop, we need to start Playwright in a way that doesn't conflict
                # Playwright sync API can't run inside an asyncio loop, so we'll start it in a thread
                logger.warning(
                    "Detected running asyncio loop. Starting Playwright in a separate thread."
                )
                playwright_result = [None]
                exception_result = [None]
                
                def start_playwright():
                    try:
                        playwright_result[0] = sync_playwright().start()
                    except Exception as e:
                        exception_result[0] = e
                
                thread = threading.Thread(target=start_playwright, daemon=False)
                thread.start()
                thread.join()
                
                if exception_result[0]:
                    raise exception_result[0]
                cls._playwright = playwright_result[0]
            except RuntimeError:
                # No running loop, safe to start Playwright normally
                cls._playwright = sync_playwright().start()
            
            cls._initialized = True
            logger.info(
                "Test suite initialized. API Base URL: %s",
                cls._config.api_base_url,
            )
            
    def setup_method(self, method=None):
        """Setup method called before each test (pytest fixture)."""
        # Ensure static resources are initialized
        self._ensure_initialized()
        
        test_name = method.__name__ if method else "unknown"
        logger.info("=" * 80)
        logger.info("Starting test: %s.%s", self.__class__.__name__, test_name)
        logger.info("=" * 80)

        # Get OAuth scopes from test method or class (if using decorators)
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

    def teardown_method(self, method=None):
        """Teardown method called after each test (pytest fixture)."""
        test_name = method.__name__ if method else "unknown"
        logger.info("=" * 80)
        logger.info("Completing test: %s.%s", self.__class__.__name__, test_name)
        logger.info("=" * 80)
        if self._api_request_context:
            self._api_request_context.dispose()
        if self._unauthenticated_api_request_context:
            self._unauthenticated_api_request_context.dispose()

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

    @property
    def authenticated_request(self) -> PlaywrightApiRequest:
        """
        Get a fluent API request builder with authentication.

        Returns:
            PlaywrightApiRequest builder for authenticated API calls
        """
        
        # Get JWT token for authentication with scopes
        access_token = self._auth_service.get_access_token(
            scopes=self._scopes, bypass_cache=self._bypass_cache
        )

        # Create API request context with base configuration
        self._api_request_context = self.playwright.request.new_context(
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

        return PlaywrightApiRequest(self._api_request_context)

    @property
    def unauthenticated_request(self) -> PlaywrightApiRequest:
        """
        Get a fluent API request builder without authentication.

        Creates an unauthenticated API request context (lazily) that does not include
        the Authorization header. Useful for testing unauthorized access scenarios.

        Returns:
            PlaywrightApiRequest builder for unauthenticated API calls
        """
        if self._unauthenticated_api_request_context is None:
            # Create API request context without authentication
            self._unauthenticated_api_request_context = (
                self.playwright.request.new_context(
                    base_url=self.config.api_base_url,
                    extra_http_headers={"Content-Type": "application/json"},
                    timeout=self.config.test_timeout,
                    ignore_https_errors=True,  # Use only in test environments
                )
            )
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
        return self._template_service.render(template_path, context or {})

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
        return BaseApiTest._config

    @property
    def auth_service(self):
        """Get the authentication service."""
        return BaseApiTest._auth_service

    @property
    def template_service(self):
        """Get the template service."""
        return BaseApiTest._template_service

    @property
    def playwright(self) -> Playwright:
        """Get the Playwright instance."""
        return BaseApiTest._playwright

