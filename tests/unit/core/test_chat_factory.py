from datetime import datetime

from llm_cli.core.chat_factory import ChatFactory


def test_create_new_chat_uses_consistent_defaults():
    now = datetime(2026, 2, 24, 15, 30, 45)
    factory = ChatFactory(
        now_fn=lambda: now,
        uuid_fn=lambda: "12345678-dead-beef-cafe-0123456789ab",
    )

    chat = factory.create_new_chat("sonnet", "You are helpful.")

    assert chat.metadata.id == "20260224_153045_12345678"
    assert chat.metadata.title == "Chat 2026-02-24 15:30"
    assert chat.metadata.created_at == now
    assert chat.metadata.updated_at == now
    assert chat.metadata.model == "sonnet"
    assert chat.metadata.message_count == 0
    assert chat.pending_system_prompt == "You are helpful."
    assert chat.messages == []
