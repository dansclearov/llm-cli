"""Factory helpers for constructing new chat sessions."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from llm_cli.core.session import Chat, ChatMetadata


@dataclass
class ChatFactory:
    """Create new chat objects with consistent metadata defaults."""

    now_fn: Callable[[], datetime] = datetime.now
    uuid_fn: Callable[[], Any] = field(default=uuid.uuid4)

    def create_new_chat(self, model: str, system_message: str) -> Chat:
        """Create a new unsaved chat with a placeholder title."""
        now = self.now_fn()
        chat_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{str(self.uuid_fn())[:8]}"

        metadata = ChatMetadata(
            id=chat_id,
            title=f"Chat {now.strftime('%Y-%m-%d %H:%M')}",
            created_at=now,
            updated_at=now,
            model=model,
            message_count=0,
        )
        return Chat(metadata=metadata, pending_system_prompt=system_message)
