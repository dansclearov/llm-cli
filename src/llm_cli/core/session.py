"""Chat session management."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)

from llm_cli.config.settings import Config
from llm_cli.core.message_utils import (
    convert_legacy_messages,
    count_non_system_messages,
    deserialize_model_messages,
    serialize_model_messages,
)
from llm_cli.exceptions import ChatNotFoundError


@dataclass
class ChatMetadata:
    """Metadata for a chat session."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    model: str
    message_count: int
    smart_title_generated: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "model": self.model,
            "message_count": self.message_count,
            "smart_title_generated": self.smart_title_generated,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ChatMetadata":
        return cls(
            id=data["id"],
            title=data["title"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            model=data["model"],
            message_count=data["message_count"],
            smart_title_generated=data.get("smart_title_generated", False),
        )


@dataclass
class Chat:
    """A chat session with messages and metadata."""

    metadata: ChatMetadata
    messages: List[ModelMessage] = field(default_factory=list)
    pending_system_prompt: Optional[str] = None

    @property
    def chat_dir(self) -> Path:
        """Get the directory for this chat."""
        config = Config()
        return Path(config.chat_dir) / self.metadata.id

    def append_user_message(self, content: str) -> None:
        """Append a user message, injecting system prompt if pending."""
        parts = []
        if self.pending_system_prompt:
            parts.append(SystemPromptPart(self.pending_system_prompt))
            self.pending_system_prompt = None
        parts.append(UserPromptPart(content))
        self.messages.append(ModelRequest(parts=parts))

    def append_assistant_response(
        self, response: ModelResponse | str, *, allow_empty: bool = False
    ) -> None:
        """Append an assistant response."""
        if isinstance(response, ModelResponse):
            self.messages.append(response)
            return

        if not response and not allow_empty:
            return

        parts = []
        if response:
            parts.append(TextPart(content=response))
        self.messages.append(ModelResponse(parts=parts))

    def should_be_saved(self) -> bool:
        """Check if chat should be saved (has non-system messages)."""
        return count_non_system_messages(self.messages) > 0

    def save(self) -> None:
        """Save chat to disk only if it has non-system messages."""
        if not self.should_be_saved():
            return

        chat_dir = self.chat_dir
        chat_dir.mkdir(parents=True, exist_ok=True)

        # Update metadata
        self.metadata.updated_at = datetime.now()
        self.metadata.message_count = count_non_system_messages(self.messages)

        # Track if we've generated smart title to avoid regenerating
        if not hasattr(self.metadata, "smart_title_generated"):
            self.metadata.smart_title_generated = False

        # Save metadata
        with open(chat_dir / "metadata.json", "w") as f:
            json.dump(self.metadata.to_dict(), f, indent=2)

        # Save messages (pydantic-ai structure)
        with open(chat_dir / "messages.json", "w") as f:
            json.dump(serialize_model_messages(self.messages), f, indent=2)

    @classmethod
    def load(cls, chat_id: str) -> "Chat":
        """Load chat from disk."""
        config = Config()
        chat_dir = Path(config.chat_dir) / chat_id

        if not chat_dir.exists():
            raise ChatNotFoundError(f"Chat not found: {chat_id}")

        # Load metadata
        with open(chat_dir / "metadata.json", "r") as f:
            metadata = ChatMetadata.from_dict(json.load(f))

        # Load messages
        with open(chat_dir / "messages.json", "r") as f:
            raw_messages = json.load(f)

        if (
            raw_messages
            and isinstance(raw_messages, list)
            and isinstance(raw_messages[0], dict)
            and "kind" in raw_messages[0]
        ):
            messages = deserialize_model_messages(raw_messages)
        else:
            messages = convert_legacy_messages(raw_messages)

        return cls(metadata=metadata, messages=messages)
