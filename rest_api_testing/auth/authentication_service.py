"""Service for authenticating with PING Federate and retrieving JWT tokens."""

import asyncio
import logging
import time
from typing import Optional, Dict
from dataclasses import dataclass
from playwright.async_api import Playwright, APIRequestContext, async_playwright
from rest_api_testing.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class TokenCacheEntry:
    """Cache entry to store token and expiry time."""

    token: str
    expiry_time: float

    def is_valid(self) -> bool:
        """Check if the token is still valid."""
        return time.time() < self.expiry_time


class AuthenticationService:
    """Service for authenticating with PING Federate and retrieving JWT tokens."""

    _instance: Optional["AuthenticationService"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        """Initialize the authentication service."""
        self.config = get_config()
        self._playwright: Optional[Playwright] = None
        self._api_request_context: Optional[APIRequestContext] = None
        self._token_cache: Dict[str, TokenCacheEntry] = {}
        self._playwright_lock = asyncio.Lock()

    async def _ensure_playwright(self) -> None:
        """Ensure Playwright is initialized (async)."""
        if self._playwright is None:
            async with self._playwright_lock:
                if self._playwright is None:
                    self._playwright = await async_playwright().start()
                    # Create a basic API request context for token requests
                    self._api_request_context = await self._playwright.request.new_context(
                        ignore_https_errors=True  # Use only in test environments
                    )

    @classmethod
    def get_instance(cls) -> "AuthenticationService":
        """Get singleton instance of AuthenticationService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_access_token(
        self, scopes: Optional[list[str]] = None, bypass_cache: bool = False
    ) -> str:
        """
        Retrieve a JWT token from PING Federate using client credentials.

        Args:
            scopes: OAuth scopes to include in the token request
            bypass_cache: If True, bypasses the token cache and fetches a new token

        Returns:
            JWT access token
        """
        await self._ensure_playwright()
        
        scopes = scopes or []
        scope_key = self._create_scope_key(scopes)

        # Check cache if not bypassing
        if not bypass_cache:
            cached_entry = self._token_cache.get(scope_key)
            if cached_entry and cached_entry.is_valid():
                logger.debug(
                    "Using cached JWT token for scopes: %s",
                    ", ".join(scopes) if scopes else "none",
                )
                return cached_entry.token
            elif cached_entry:
                logger.debug(
                    "Cached token expired for scopes: %s, fetching new token",
                    ", ".join(scopes) if scopes else "none",
                )
                del self._token_cache[scope_key]
        else:
            logger.debug("Bypassing token cache as requested")

        logger.info(
            "Fetching new JWT token from PING Federate with scopes: %s",
            ", ".join(scopes) if scopes else "none",
        )

        base_url = self.config.ping_federate_base_url
        token_endpoint = self.config.ping_federate_token_endpoint
        client_id = self.config.ping_federate_client_id
        client_secret = self.config.ping_federate_client_secret
        grant_type = self.config.ping_federate_grant_type

        if not client_id or not client_secret:
            raise ValueError(
                "PING Federate client ID and secret must be configured. "
                "Set PING_FEDERATE_CLIENT_ID and PING_FEDERATE_CLIENT_SECRET "
                "environment variables or in a .env file"
            )

        token_url = f"{base_url}{token_endpoint}"

        # Build form data
        form_data: Dict[str, str] = {
            "grant_type": grant_type,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        # Add scopes if provided
        if scopes:
            form_data["scope"] = " ".join(scopes)
            logger.debug("Including scopes in token request: %s", " ".join(scopes))

        # Make token request
        response = await self._api_request_context.post(
            token_url,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status != 200:
            response_text = await response.text()
            logger.error(
                "Failed to retrieve token. Status: %d, Body: %s",
                response.status,
                response_text,
            )
            raise RuntimeError(
                f"Failed to retrieve JWT token from PING Federate. Status: {response.status}"
            )

        # Parse JSON response
        try:
            json_response = await response.json()
        except Exception as e:
            response_text = await response.text()
            logger.error("Failed to parse token response as JSON: %s", response_text)
            raise RuntimeError("Failed to parse PING Federate response") from e

        access_token = json_response.get("access_token")
        if not access_token:
            raise RuntimeError("Access token not found in PING Federate response")

        # Cache the token per scope combination (assuming 1 hour expiry)
        # In production, you should parse the JWT to get the actual expiry time
        expiry_time = time.time() + (55 * 60)  # 55 minutes cache
        self._token_cache[scope_key] = TokenCacheEntry(access_token, expiry_time)

        logger.info(
            "Successfully retrieved and cached JWT token for scopes: %s",
            ", ".join(scopes) if scopes else "none",
        )
        return access_token

    def _create_scope_key(self, scopes: list[str]) -> str:
        """
        Create a cache key from the scope list.

        Args:
            scopes: List of scope strings

        Returns:
            Cache key string
        """
        if not scopes:
            return ""
        # Sort scopes to ensure consistent cache keys
        return " ".join(sorted(scopes))

    def invalidate_token(self, scopes: Optional[list[str]] = None) -> None:
        """
        Invalidate the cached token for the specified scopes.

        Args:
            scopes: OAuth scopes to invalidate cache for
        """
        scopes = scopes or []
        scope_key = self._create_scope_key(scopes)
        if scope_key in self._token_cache:
            del self._token_cache[scope_key]
            logger.info(
                "Invalidated cached JWT token for scopes: %s",
                ", ".join(scopes) if scopes else "none",
            )

    def invalidate_all_tokens(self) -> None:
        """Invalidate all cached tokens."""
        logger.info("Invalidating all cached JWT tokens")
        self._token_cache.clear()
