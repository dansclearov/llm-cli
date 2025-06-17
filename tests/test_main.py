import json
from unittest.mock import mock_open, patch

import pytest

from llm_cli.config import Config
from llm_cli.main import ChatHistory, InputHandler, LLMClient


# Fixtures
@pytest.fixture
def config():
    return Config(
        chat_dir="/test/chats",
        temp_file="test_session.json",
        max_history_pairs=3,
    )


@pytest.fixture
def chat_history(config):
    return ChatHistory(config)


@pytest.fixture
def llm_client():
    return LLMClient()


# Test Config
def test_config_defaults():
    config = Config()
    assert isinstance(config.chat_dir, str)
    assert isinstance(config.temp_file, str)
    assert config.max_history_pairs == 3


# Test ChatHistory
def test_chat_history_init(chat_history):
    assert chat_history.messages == []


def test_chat_history_save(chat_history, tmp_path):
    # Setup
    chat_history.config.chat_dir = str(tmp_path)
    chat_history.messages = [
        {"role": "system", "content": "test system"},
        {"role": "user", "content": "test user"},
    ]

    # Execute
    chat_history.save("test.json")

    # Verify
    saved_file = tmp_path / "test.json"
    assert saved_file.exists()
    with open(saved_file) as f:
        saved_data = json.load(f)
    assert saved_data == chat_history.messages


def test_chat_history_load(chat_history):
    test_messages = [
        {"role": "system", "content": "test system"},
        {"role": "user", "content": "test user"},
    ]
    mock_file = mock_open(read_data=json.dumps(test_messages))

    with patch("builtins.open", mock_file):
        chat_history.load("test.json")

    assert chat_history.messages == test_messages


def test_chat_history_load_file_not_found(chat_history):
    with pytest.raises(FileNotFoundError):
        chat_history.load("nonexistent.json")


def test_chat_history_append_from_file(chat_history):
    original_messages = [
        {"role": "system", "content": "system1"},
        {"role": "user", "content": "user1"},
    ]
    append_messages = [
        {"role": "system", "content": "system2"},
        {"role": "user", "content": "user2"},
        {"role": "assistant", "content": "assistant2"},
    ]
    chat_history.messages = original_messages.copy()

    mock_file = mock_open(read_data=json.dumps(append_messages))
    with patch("builtins.open", mock_file):
        chat_history.append_from_file("append.json")

    # Check that system message was filtered out and other messages were appended
    expected_messages = original_messages + [
        msg for msg in append_messages if msg["role"] != "system"
    ]
    assert chat_history.messages == expected_messages


# Test LLMClient
def test_llm_client_init():
    client = LLMClient()
    assert client.registry is not None


# Test InputHandler
def test_parse_command_valid():
    handler = InputHandler()
    command, args = handler.parse_command("%save test.json")
    assert command == "save"
    assert args == "test.json"


def test_parse_command_invalid():
    handler = InputHandler()
    with pytest.raises(ValueError):
        handler.parse_command("%invalid test")


def test_parse_command_no_args():
    handler = InputHandler()
    command, args = handler.parse_command("%save")
    assert command == "save"
    assert args is None


def test_parse_not_command():
    handler = InputHandler()
    command, args = handler.parse_command("regular input")
    assert command is None
    assert args is None


# Integration-style tests
@patch("builtins.input")
@patch("builtins.print")
def test_input_handler_single_line(mock_print, mock_input):
    mock_input.return_value = "test input"
    handler = InputHandler()
    result = handler.get_user_input()
    assert result == "test input"


@patch("builtins.input")
@patch("builtins.print")
def test_input_handler_multi_line(mock_print, mock_input):
    mock_input.side_effect = [">start", "line 1", "line 2", ">>"]
    handler = InputHandler()
    result = handler.get_user_input()
    assert result == "line 1\nline 2"
