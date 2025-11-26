"""Logging setup and configuration for the REST API testing framework."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(
    log_directory: str = "logs",
    log_level: str = "INFO",
    log_to_console: bool = True,
) -> None:
    """
    Set up logging configuration with file and console handlers.

    Args:
        log_directory: Directory where log files will be written
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_console: Whether to log to console in addition to file
    """
    # Create log directory if it doesn't exist
    log_path = Path(log_directory)
    log_path.mkdir(parents=True, exist_ok=True)

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"api_test_{timestamp}.log"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(
        fmt="%(levelname)s - %(name)s - %(message)s",
    )

    # File handler with rotation (10MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized. Log file: %s", log_file)
    logger.info("Log level: %s", log_level)


def log_config(config) -> None:
    """
    Log the current configuration (masking sensitive values).

    Args:
        config: TestConfig instance to log
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("TEST CONFIGURATION")
    logger.info("=" * 80)
    logger.info("API Base URL: %s", config.api_base_url)
    logger.info("Test Timeout: %d ms", config.test_timeout)
    logger.info("Connection Timeout: %d ms", config.test_connection_timeout)
    logger.info("PING Federate Base URL: %s", config.ping_federate_base_url)
    logger.info("PING Federate Token Endpoint: %s", config.ping_federate_token_endpoint)
    logger.info("PING Federate Grant Type: %s", config.ping_federate_grant_type)
    logger.info(
        "PING Federate Client ID: %s",
        config.ping_federate_client_id[:10] + "..." if config.ping_federate_client_id else "Not set",
    )
    logger.info(
        "PING Federate Client Secret: %s",
        "***" if config.ping_federate_client_secret else "Not set",
    )
    logger.info("Log Directory: %s", config.log_directory)
    logger.info("Log Level: %s", config.log_level)
    logger.info("Log Request Body: %s", config.log_request_body)
    logger.info("Log Response Body: %s", config.log_response_body)
    logger.info("=" * 80)

