from unittest.mock import patch

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import CompleteStyle

from llm_cli.local_commands import SlashCommandCompleter
from llm_cli.ui.input_handler import InputHandler


def test_get_user_input_preserves_whitespace():
    input_handler = InputHandler()

    with patch("llm_cli.ui.input_handler.prompt", return_value="  padded message  "):
        assert input_handler.get_user_input() == "  padded message  "


def test_get_user_input_maps_eof_to_keyboard_interrupt():
    input_handler = InputHandler()

    with patch("llm_cli.ui.input_handler.prompt", side_effect=EOFError):
        with pytest.raises(KeyboardInterrupt):
            input_handler.get_user_input()


def test_get_user_input_passes_slash_command_completer():
    input_handler = InputHandler()

    with patch(
        "llm_cli.ui.input_handler.prompt", return_value="/bookmark"
    ) as mock_prompt:
        assert input_handler.get_user_input() == "/bookmark"

    assert isinstance(mock_prompt.call_args.kwargs["completer"], SlashCommandCompleter)
    assert mock_prompt.call_args.kwargs["complete_style"] == CompleteStyle.READLINE_LIKE


def test_slash_command_completer_suggests_known_commands_only():
    completer = SlashCommandCompleter()
    completions = list(
        completer.get_completions(
            Document("/bo"),
            CompleteEvent(completion_requested=True),
        )
    )

    assert [completion.text for completion in completions] == ["/bookmark"]

    non_command_completions = list(
        completer.get_completions(
            Document("plain message"),
            CompleteEvent(completion_requested=True),
        )
    )
    assert non_command_completions == []
