from datetime import datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock, patch

import pytest
from pydantic_ai.messages import ModelResponse, TextPart

from llm_cli.app import handle_chat_selection, run_chat_loop
from llm_cli.config.settings import Config
from llm_cli.core.session import Chat, ChatMetadata
from llm_cli.exceptions import ChatNotFoundError
from llm_cli.llm_types import ChatOptions


def test_run_chat_loop_skips_empty_input():
    metadata = ChatMetadata(
        id="test-chat",
        title="Chat 2026-02-14 00:00",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        model="sonnet",
        message_count=0,
    )
    current_chat = Chat(metadata=metadata)

    args = SimpleNamespace(model="sonnet")
    chat_manager = Mock()
    llm_client = Mock()
    input_handler = Mock()
    input_handler.get_user_input.side_effect = ["", KeyboardInterrupt()]
    config = Config()

    run_chat_loop(
        current_chat=current_chat,
        args=args,
        chat_manager=chat_manager,
        llm_client=llm_client,
        input_handler=input_handler,
        chat_options=ChatOptions(),
        prompt_str="You are helpful.",
        config=config,
        active_model="sonnet",
        is_new_chat=True,
    )

    llm_client.chat.assert_not_called()
    assert current_chat.messages == []


def test_run_chat_loop_skips_whitespace_only_input():
    metadata = ChatMetadata(
        id="test-chat-whitespace",
        title="Chat 2026-02-14 00:00",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        model="sonnet",
        message_count=0,
    )
    current_chat = Chat(metadata=metadata)

    args = SimpleNamespace(model="sonnet")
    chat_manager = Mock()
    llm_client = Mock()
    input_handler = Mock()
    input_handler.get_user_input.side_effect = ["   ", KeyboardInterrupt()]
    config = Config()

    run_chat_loop(
        current_chat=current_chat,
        args=args,
        chat_manager=chat_manager,
        llm_client=llm_client,
        input_handler=input_handler,
        chat_options=ChatOptions(),
        prompt_str="You are helpful.",
        config=config,
        active_model="sonnet",
        is_new_chat=True,
    )

    llm_client.chat.assert_not_called()
    assert current_chat.messages == []


def test_run_chat_loop_uses_active_model_for_resumed_chat():
    metadata = ChatMetadata(
        id="test-chat-resume",
        title="Existing chat",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        model="sonnet",
        message_count=4,
    )
    current_chat = Chat(metadata=metadata)
    current_chat.append_user_message("Earlier user message")
    current_chat.append_assistant_response("Earlier assistant message")

    args = SimpleNamespace(model="gpt")
    chat_manager = Mock()
    llm_client = Mock()
    llm_client.chat.return_value = ModelResponse(parts=[TextPart(content="new reply")])
    input_handler = Mock()
    input_handler.get_user_input.side_effect = ["Next question", KeyboardInterrupt()]
    config = Config()

    with patch.object(Chat, "save", return_value=None):
        run_chat_loop(
            current_chat=current_chat,
            args=args,
            chat_manager=chat_manager,
            llm_client=llm_client,
            input_handler=input_handler,
            chat_options=ChatOptions(),
            prompt_str="You are helpful.",
            config=config,
            active_model="sonnet",
            is_new_chat=False,
        )

    assert llm_client.chat.call_args[0][1] == "sonnet"


def test_handle_chat_selection_exits_for_missing_explicit_resume(monkeypatch):
    args = SimpleNamespace(resume="missing-id", **{"continue": False})
    chat_manager = Mock()

    def raise_not_found(chat_id: str):
        raise ChatNotFoundError(f"Chat not found: {chat_id}")

    monkeypatch.setattr("llm_cli.app.Chat.load", raise_not_found)

    with pytest.raises(SystemExit) as exc_info:
        handle_chat_selection(args, chat_manager)

    assert cast(SystemExit, exc_info.value).code == 1
