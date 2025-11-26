"""
REST API Testing Framework for Python

A Python-based REST API testing framework using Playwright, pytest, and Jinja2.
"""

from rest_api_testing.base_api_test import BaseApiTest
from rest_api_testing.config import TestConfig
from rest_api_testing.auth import AuthenticationService
from rest_api_testing.template import TemplateService, TemplateException
from rest_api_testing.playwright_api import PlaywrightApiRequest

__version__ = "1.0.0"

__all__ = [
    "BaseApiTest",
    "TestConfig",
    "AuthenticationService",
    "TemplateService",
    "TemplateException",
    "PlaywrightApiRequest",
]

