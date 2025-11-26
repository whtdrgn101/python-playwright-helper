"""Base API test class for REST API testing."""

import logging
from typing import Optional, List
from playwright.sync_api import Playwright, APIRequestContext, sync_playwright
from rest_api_testing.config import get_config
from rest_api_testing.auth import AuthenticationService
from rest_api_testing.template import TemplateService
from rest_api_testing.playwright_api import PlaywrightApiRequest

logger = logging.getLogger(__name__)


class BaseApiTest:
    """Base test class that sets up Playwright API testing configuration and authentication."""

    _config = None
    _auth_service = None
    _template_service = None
    _playwright: Optional[Playwright] = None

    def __init__(self):
        """Initialize the base API test."""
        # Initialize static resources if not already done
        if BaseApiTest._config is None:
            BaseApiTest._config = get_config()
            BaseApiTest._auth_service = AuthenticationService.get_instance()
            BaseApiTest._template_service = TemplateService.get_instance()
            BaseApiTest._playwright = sync_playwright().start()
            logger.info(
                "Test suite initialized. API Base URL: %s",
                BaseApiTest._config.api_base_url,
            )

        self._api_request_context: Optional[APIRequestContext] = None
        self._unauthenticated_api_request_context: Optional[APIRequestContext] = None

    def setup_method(self):
        """Setup method called before each test (pytest fixture)."""
        logger.info("Setting up test: %s", self.__class__.__name__)

        # Get OAuth scopes from test method or class (if using decorators)
        scopes = self._extract_scopes()

        # Get JWT token for authentication with scopes
        access_token = self.auth_service.get_access_token(scopes=scopes)

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

        logger.info("Test setup completed")

    def teardown_method(self):
        """Teardown method called after each test (pytest fixture)."""
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
        if self._api_request_context is None:
            raise RuntimeError(
                "API request context not initialized. Call setup_method() first."
            )
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

    def _extract_scopes(self) -> Optional[List[str]]:
        """
        Extract OAuth scopes from test method or class.

        This can be extended to support decorators or annotations.

        Returns:
            List of OAuth scopes, or None if not specified
        """
        # For now, return None. Can be extended to support decorators
        # Example: check for @oauth_scopes decorator on method or class
        return None

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

