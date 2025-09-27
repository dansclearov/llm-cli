from unittest.mock import Mock

from llm_cli.core.client import LLMClient


class TestLLMClient:
    def test_init(self):
        mock_registry = Mock()
        client = LLMClient(mock_registry)

        assert client.registry == mock_registry
        assert client.interrupt_handler is None
