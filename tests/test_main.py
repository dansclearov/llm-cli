import json
from unittest.mock import mock_open, patch

import pytest

from llm_cli.config.settings import Config
from llm_cli.core.client import LLMClient
from llm_cli.ui.input_handler import InputHandler


# Test Config
def test_config_defaults():
    config = Config()
    assert isinstance(config.chat_dir, str)
    assert isinstance(config.temp_file, str)
    assert config.max_history_pairs == 3


# Test LLMClient
def test_llm_client_init():
    client = LLMClient()
    assert client.registry is not None
