import json
from unittest.mock import mock_open, patch

import pytest

from llm_cli.config.settings import Config, setup_providers
from llm_cli.core.client import LLMClient
from llm_cli.ui.input_handler import InputHandler


# Test Config
def test_config_defaults():
    config = Config()
    assert isinstance(config.chat_dir, str)


# Test LLMClient
def test_llm_client_init():
    registry = setup_providers()
    client = LLMClient(registry)
    assert client.registry is not None
    assert client.registry == registry
