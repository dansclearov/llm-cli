from datetime import datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest
from pydantic_ai.messages import ModelResponse, TextPart

from llm_cli.app import handle_chat_selection, run_chat_loop
from llm_cli.config.settings import Config
from llm_cli.core.session import Chat, ChatMetadata
from llm_cli.exceptions import ChatNotFoundError
from llm_cli.llm_types import ChatOptions, ModelCapabilities


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

    chat_manager = Mock()
    llm_client = Mock()
    input_handler = Mock()
    input_handler.get_user_input.side_effect = ["", KeyboardInterrupt()]
    config = Config()

    run_chat_loop(
        current_chat=current_chat,
        chat_manager=chat_manager,
        llm_client=llm_client,
        input_handler=input_handler,
        chat_options=ChatOptions(),
        prompt_str="You are helpful.",
        config=config,
        active_model="sonnet",
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

    chat_manager = Mock()
    llm_client = Mock()
    input_handler = Mock()
    input_handler.get_user_input.side_effect = ["   ", KeyboardInterrupt()]
    config = Config()

    run_chat_loop(
        current_chat=current_chat,
        chat_manager=chat_manager,
        llm_client=llm_client,
        input_handler=input_handler,
        chat_options=ChatOptions(),
        prompt_str="You are helpful.",
        config=config,
        active_model="sonnet",
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
    current_chat.metadata.set_model_capabilities_snapshot(
        ModelCapabilities(
            supports_search=True,
            supports_thinking=False,
            extra_params={"example": True},
        )
    )
    current_chat.append_user_message("Earlier user message")
    current_chat.append_assistant_response("Earlier assistant message")

    chat_manager = Mock()
    llm_client = Mock()
    llm_client.chat.return_value = ModelResponse(parts=[TextPart(content="new reply")])
    input_handler = Mock()
    input_handler.get_user_input.side_effect = ["Next question", KeyboardInterrupt()]
    config = Config()

    run_chat_loop(
        current_chat=current_chat,
        chat_manager=chat_manager,
        llm_client=llm_client,
        input_handler=input_handler,
        chat_options=ChatOptions(),
        prompt_str="You are helpful.",
        config=config,
        active_model="sonnet",
    )

    assert llm_client.chat.call_args[0][1] == "sonnet"
    capabilities_override = llm_client.chat.call_args.kwargs["capabilities_override"]
    assert capabilities_override is not None
    assert capabilities_override.supports_search is True
    assert capabilities_override.supports_thinking is False
    assert capabilities_override.extra_params == {"example": True}


def test_handle_chat_selection_exits_for_missing_explicit_resume():
    args = SimpleNamespace(resume="missing-id", **{"continue": False})
    chat_manager = Mock()
    chat_manager.load_chat.side_effect = ChatNotFoundError("Chat not found: missing-id")

    with pytest.raises(SystemExit) as exc_info:
        handle_chat_selection(args, chat_manager)

    assert cast(SystemExit, exc_info.value).code == 1


def test_run_chat_loop_discards_user_message_on_request_error():
    metadata = ChatMetadata(
        id="test-chat-error",
        title="Chat 2026-02-14 00:00",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        model="sonnet",
        message_count=0,
    )
    current_chat = Chat(metadata=metadata)

    chat_manager = Mock()
    llm_client = Mock()
    llm_client.chat.side_effect = RuntimeError("upstream failed")
    input_handler = Mock()
    input_handler.get_user_input.side_effect = ["Hello", KeyboardInterrupt()]
    config = Config()

    run_chat_loop(
        current_chat=current_chat,
        chat_manager=chat_manager,
        llm_client=llm_client,
        input_handler=input_handler,
        chat_options=ChatOptions(),
        prompt_str="You are helpful.",
        config=config,
        active_model="sonnet",
    )

    # Failed requests should not leave orphan user messages behind.
    assert current_chat.messages == []
