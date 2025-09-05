"""Pytest configuration and fixtures."""

import os
import tempfile
import pytest
from unittest.mock import patch, Mock

from llm_cli.providers.base import LLMProvider, ModelCapabilities, StreamChunk, ChatOptions


class MockProvider(LLMProvider):
    """Mock provider for testing."""
    
    def get_capabilities(self, model: str) -> ModelCapabilities:
        return ModelCapabilities(
            supports_search=False,
            supports_thinking=False,
            max_tokens=4096
        )
    
    def stream_response(self, messages, model, options):
        yield StreamChunk(content="Hello")
        yield StreamChunk(content=" world!")


@pytest.fixture
def mock_provider():
    """Provide a mock LLM provider."""
    return MockProvider()


@pytest.fixture
def temp_config_dir():
    """Provide a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir