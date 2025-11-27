"""Pytest configuration for tests."""

import pytest


def pytest_configure(config):
    """Configure pytest to disable asyncio plugin."""
    # Explicitly disable pytest-asyncio if it's installed
    try:
        config.pluginmanager.set_blocked("pytest_asyncio")
    except Exception:
        pass


def pytest_collection_modifyitems(config, items):
    """Modify test items if needed."""
    pass

