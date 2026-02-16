from unittest.mock import patch

import pytest

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
