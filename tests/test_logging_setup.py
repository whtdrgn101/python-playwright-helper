"""Unit tests for logging_setup module."""

import pytest
import logging
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from rest_api_testing.logging_setup import setup_logging, log_config
from rest_api_testing.config import TestConfig


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    root_logger = logging.getLogger()
    # Store original handlers
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    
    yield
    
    # Restore original configuration
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    for handler in original_handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(original_level)


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_creates_log_directory(self):
        """Test that setup_logging creates log directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, "new_logs")
            
            assert not os.path.exists(log_dir)
            
            setup_logging(log_directory=log_dir, log_to_console=False)
            
            assert os.path.exists(log_dir)
            assert os.path.isdir(log_dir)

    def test_setup_logging_sets_log_level(self):
        """Test that setup_logging sets the correct log level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(
                log_directory=temp_dir,
                log_level="DEBUG",
                log_to_console=False
            )
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG

    def test_setup_logging_sets_info_level(self):
        """Test that setup_logging sets INFO level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(
                log_directory=temp_dir,
                log_level="INFO",
                log_to_console=False
            )
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO

    def test_setup_logging_sets_warning_level(self):
        """Test that setup_logging sets WARNING level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(
                log_directory=temp_dir,
                log_level="WARNING",
                log_to_console=False
            )
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.WARNING

    def test_setup_logging_sets_error_level(self):
        """Test that setup_logging sets ERROR level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(
                log_directory=temp_dir,
                log_level="ERROR",
                log_to_console=False
            )
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.ERROR

    def test_setup_logging_creates_file_handler(self):
        """Test that setup_logging creates a file handler."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_to_console=False)
            
            root_logger = logging.getLogger()
            
            # Should have at least one handler (file handler)
            assert len(root_logger.handlers) > 0

    def test_setup_logging_creates_console_handler_when_enabled(self):
        """Test that setup_logging creates console handler when enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_to_console=True)
            
            root_logger = logging.getLogger()
            
            # Should have both file and console handlers
            assert len(root_logger.handlers) >= 2

    def test_setup_logging_no_console_handler_when_disabled(self):
        """Test that console handler is not created when disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_to_console=False)
            
            root_logger = logging.getLogger()
            
            # Find console handlers
            console_handlers = [
                h for h in root_logger.handlers
                if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler)
            ]
            
            assert len(console_handlers) == 0

    def test_setup_logging_invalid_log_level_defaults_to_info(self):
        """Test that invalid log level defaults to INFO."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(
                log_directory=temp_dir,
                log_level="INVALID_LEVEL",
                log_to_console=False
            )
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO

    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup_logging clears existing handlers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root_logger = logging.getLogger()
            
            # Add a dummy handler
            dummy_handler = logging.StreamHandler()
            root_logger.addHandler(dummy_handler)
            assert len(root_logger.handlers) >= 1
            
            # Call setup_logging
            setup_logging(log_directory=temp_dir, log_to_console=False)
            
            # Dummy handler should be removed
            assert dummy_handler not in root_logger.handlers

    def test_setup_logging_creates_log_file(self):
        """Test that setup_logging creates a log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_to_console=False)
            
            # Check that a log file was created
            log_files = list(Path(temp_dir).glob("*.log"))
            assert len(log_files) > 0

    def test_setup_logging_log_file_has_timestamp(self):
        """Test that log file name includes timestamp."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_to_console=False)
            
            log_files = list(Path(temp_dir).glob("api_test_*.log"))
            assert len(log_files) > 0

    def test_setup_logging_writes_to_file(self):
        """Test that logs are written to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_level="INFO", log_to_console=False)
            
            logger = logging.getLogger(__name__)
            logger.info("Test log message")
            
            # Check that log file has content
            log_files = list(Path(temp_dir).glob("*.log"))
            assert len(log_files) > 0
            
            with open(log_files[0], "r") as f:
                content = f.read()
                assert "Test log message" in content

    def test_setup_logging_file_handler_has_formatter(self):
        """Test that file handler has proper formatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_to_console=False)
            
            root_logger = logging.getLogger()
            
            # Find file handler
            file_handlers = [
                h for h in root_logger.handlers
                if isinstance(h, logging.handlers.RotatingFileHandler)
            ]
            
            assert len(file_handlers) > 0
            assert file_handlers[0].formatter is not None

    def test_setup_logging_console_handler_has_formatter(self):
        """Test that console handler has proper formatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_to_console=True)
            
            root_logger = logging.getLogger()
            
            # Find console handlers (excluding RotatingFileHandler)
            console_handlers = [
                h for h in root_logger.handlers
                if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler)
            ]
            
            assert len(console_handlers) > 0
            assert console_handlers[0].formatter is not None


class TestLogConfig:
    """Test log_config function."""

    def test_log_config_logs_configuration(self):
        """Test that log_config logs configuration values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_level="INFO", log_to_console=False)
            
            mock_config = MagicMock(spec=TestConfig)
            mock_config.api_base_url = "https://api.example.com"
            mock_config.test_timeout = 30000
            mock_config.test_connection_timeout = 5000
            mock_config.ping_federate_base_url = "https://auth.example.com"
            mock_config.ping_federate_token_endpoint = "/as/token.oauth2"
            mock_config.ping_federate_grant_type = "client_credentials"
            mock_config.ping_federate_client_id = "test-client-id"
            mock_config.ping_federate_client_secret = "secret"
            mock_config.log_directory = temp_dir
            mock_config.log_level = "INFO"
            mock_config.log_request_body = True
            mock_config.log_response_body = True
            
            with patch('rest_api_testing.logging_setup.logging.getLogger') as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger
                
                log_config(mock_config)
                
                # Verify logger methods were called
                assert mock_logger.info.called

    def test_log_config_masks_client_id(self):
        """Test that log_config masks sensitive client ID."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_level="INFO", log_to_console=False)
            
            mock_config = MagicMock(spec=TestConfig)
            mock_config.api_base_url = "https://api.example.com"
            mock_config.test_timeout = 30000
            mock_config.test_connection_timeout = 5000
            mock_config.ping_federate_base_url = "https://auth.example.com"
            mock_config.ping_federate_token_endpoint = "/as/token.oauth2"
            mock_config.ping_federate_grant_type = "client_credentials"
            mock_config.ping_federate_client_id = "verylongclientidthatshouldbemaxedout"
            mock_config.ping_federate_client_secret = "secret"
            mock_config.log_directory = temp_dir
            mock_config.log_level = "INFO"
            mock_config.log_request_body = True
            mock_config.log_response_body = True
            
            logger = logging.getLogger("rest_api_testing.logging_setup")
            
            # Capture log output
            with patch.object(logger, 'info') as mock_info:
                log_config(mock_config)
                
                # Check that the client ID was truncated with "..."
                client_id_found = False
                for call_obj in mock_info.call_args_list:
                    if len(call_obj[0]) > 1:
                        # The format string is first argument, values are in args tuple
                        if "PING Federate Client ID" in str(call_obj[0][0]):
                            # The second argument should have the masked value
                            if "..." in str(call_obj[0]):
                                client_id_found = True
                                break
                
                assert client_id_found

    def test_log_config_masks_client_secret(self):
        """Test that log_config masks client secret."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_level="INFO", log_to_console=False)
            
            mock_config = MagicMock(spec=TestConfig)
            mock_config.api_base_url = "https://api.example.com"
            mock_config.test_timeout = 30000
            mock_config.test_connection_timeout = 5000
            mock_config.ping_federate_base_url = "https://auth.example.com"
            mock_config.ping_federate_token_endpoint = "/as/token.oauth2"
            mock_config.ping_federate_grant_type = "client_credentials"
            mock_config.ping_federate_client_id = "client-id"
            mock_config.ping_federate_client_secret = "super_secret_password"
            mock_config.log_directory = temp_dir
            mock_config.log_level = "INFO"
            mock_config.log_request_body = True
            mock_config.log_response_body = True
            
            logger = logging.getLogger("rest_api_testing.logging_setup")
            
            with patch.object(logger, 'info') as mock_info:
                log_config(mock_config)
                
                # Check that secret is masked
                for call_obj in mock_info.call_args_list:
                    if len(call_obj[0]) > 0 and "Client Secret" in call_obj[0][0]:
                        # Should be masked with ***
                        assert "***" in call_obj[0]

    def test_log_config_handles_missing_client_id(self):
        """Test that log_config handles missing client ID gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_level="INFO", log_to_console=False)
            
            mock_config = MagicMock(spec=TestConfig)
            mock_config.api_base_url = "https://api.example.com"
            mock_config.test_timeout = 30000
            mock_config.test_connection_timeout = 5000
            mock_config.ping_federate_base_url = "https://auth.example.com"
            mock_config.ping_federate_token_endpoint = "/as/token.oauth2"
            mock_config.ping_federate_grant_type = "client_credentials"
            mock_config.ping_federate_client_id = None
            mock_config.ping_federate_client_secret = None
            mock_config.log_directory = temp_dir
            mock_config.log_level = "INFO"
            mock_config.log_request_body = True
            mock_config.log_response_body = True
            
            # Should not raise error
            log_config(mock_config)

    def test_log_config_logs_separator_lines(self):
        """Test that log_config includes separator lines."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_level="INFO", log_to_console=False)
            
            mock_config = MagicMock(spec=TestConfig)
            mock_config.api_base_url = "https://api.example.com"
            mock_config.test_timeout = 30000
            mock_config.test_connection_timeout = 5000
            mock_config.ping_federate_base_url = "https://auth.example.com"
            mock_config.ping_federate_token_endpoint = "/as/token.oauth2"
            mock_config.ping_federate_grant_type = "client_credentials"
            mock_config.ping_federate_client_id = "client-id"
            mock_config.ping_federate_client_secret = "secret"
            mock_config.log_directory = temp_dir
            mock_config.log_level = "INFO"
            mock_config.log_request_body = True
            mock_config.log_response_body = True
            
            logger = logging.getLogger("rest_api_testing.logging_setup")
            
            with patch.object(logger, 'info') as mock_info:
                log_config(mock_config)
                
                # Check that separator lines are logged (80 equals signs)
                separator_found = False
                for call_obj in mock_info.call_args_list:
                    if len(call_obj[0]) > 0:
                        msg = call_obj[0][0]
                        if "=" * 80 in msg or (isinstance(msg, str) and msg.count("=") >= 80):
                            separator_found = True
                            break
                
                assert separator_found

    def test_log_config_logs_all_configuration_fields(self):
        """Test that log_config logs all required configuration fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_directory=temp_dir, log_level="INFO", log_to_console=False)
            
            mock_config = MagicMock(spec=TestConfig)
            mock_config.api_base_url = "https://api.example.com"
            mock_config.test_timeout = 30000
            mock_config.test_connection_timeout = 5000
            mock_config.ping_federate_base_url = "https://auth.example.com"
            mock_config.ping_federate_token_endpoint = "/as/token.oauth2"
            mock_config.ping_federate_grant_type = "client_credentials"
            mock_config.ping_federate_client_id = "client-id"
            mock_config.ping_federate_client_secret = "secret"
            mock_config.log_directory = temp_dir
            mock_config.log_level = "INFO"
            mock_config.log_request_body = True
            mock_config.log_response_body = True
            
            logger = logging.getLogger("rest_api_testing.logging_setup")
            
            with patch.object(logger, 'info') as mock_info:
                log_config(mock_config)
                
                # Collect all logged messages
                logged_messages = []
                for call_obj in mock_info.call_args_list:
                    if len(call_obj[0]) > 0:
                        logged_messages.append(call_obj[0][0])
                
                logged_text = " ".join(str(m) for m in logged_messages)
                
                # Verify key fields are logged
                assert "API Base URL" in logged_text
                assert "Test Timeout" in logged_text
                assert "PING Federate" in logged_text


class TestSetupLoggingDefaultParameters:
    """Test setup_logging with default parameters."""

    def test_setup_logging_default_parameters(self):
        """Test setup_logging with all default parameters."""
        with patch('pathlib.Path.mkdir'):
            with patch('logging.handlers.RotatingFileHandler'):
                # Should not raise error
                setup_logging()
                
                root_logger = logging.getLogger()
                assert root_logger.level == logging.INFO

    def test_setup_logging_creates_logs_directory_by_default(self):
        """Test that setup_logging creates 'logs' directory by default."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                setup_logging(log_to_console=False)
                
                assert os.path.exists("logs")
            finally:
                os.chdir(original_cwd)
