"""Configuration management for the REST API testing framework."""

import logging
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

logger = logging.getLogger(__name__)


class TestConfig(BaseSettings):
    """Configuration class for loading test settings from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # PING Federate Configuration
    ping_federate_base_url: str = Field(
        default="",
        description="Base URL for PING Federate server",
    )
    ping_federate_token_endpoint: str = Field(
        default="/as/token.oauth2",
        description="Token endpoint path for PING Federate",
    )
    ping_federate_client_id: str = Field(
        default="",
        description="Client ID for PING Federate OAuth",
    )
    ping_federate_client_secret: str = Field(
        default="",
        description="Client secret for PING Federate OAuth",
    )
    ping_federate_grant_type: str = Field(
        default="client_credentials",
        description="OAuth grant type",
    )

    # API Base URL
    api_base_url: str = Field(
        default="",
        description="Base URL for the API under test",
    )

    # Test Configuration
    test_timeout: int = Field(
        default=30000,
        description="Request timeout in milliseconds",
    )
    test_connection_timeout: int = Field(
        default=10000,
        description="Connection timeout in milliseconds",
    )

    @classmethod
    def get_instance(cls) -> "TestConfig":
        """Get singleton instance of TestConfig."""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance

    def get_property(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a property value by key.

        Args:
            key: Property key (supports both snake_case and original field names)
            default: Default value if property not found

        Returns:
            Property value or default
        """
        # Try direct attribute access first
        if hasattr(self, key):
            value = getattr(self, key)
            return value if value else default

        # Try converting dot notation to snake_case
        snake_key = key.replace(".", "_")
        if hasattr(self, snake_key):
            value = getattr(self, snake_key)
            return value if value else default

        return default


# Global instance
_config: Optional[TestConfig] = None


def get_config() -> TestConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = TestConfig.get_instance()
        # Log configuration source
        env_file = Path(".env")
        if env_file.exists():
            logger.info("Loaded configuration from .env file")
        else:
            logger.info(
                "No .env file found. Using environment variables and defaults. "
                "Create a .env file or set environment variables for configuration."
            )
    return _config
