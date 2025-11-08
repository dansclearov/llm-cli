"""Pytest configuration and fixtures."""

import tempfile

import pytest


@pytest.fixture
def temp_config_dir():
    """Provide a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir
