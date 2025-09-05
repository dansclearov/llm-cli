import signal
from unittest.mock import Mock, MagicMock, patch
import pytest

from llm_cli.core.client import LLMClient
from llm_cli.providers.base import ChatOptions, StreamChunk, ModelCapabilities
from llm_cli.exceptions import ModelNotFoundError


class TestLLMClient:
    def test_init(self):
        mock_registry = Mock()
        client = LLMClient(mock_registry)
        
        assert client.registry == mock_registry
        assert client.interrupt_handler is None

