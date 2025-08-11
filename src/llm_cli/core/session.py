"""Chat session management."""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from llm_cli.config.settings import Config
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
    preview: str  # First user message preview
    smart_title_generated: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "model": self.model,
            "message_count": self.message_count,
            "preview": self.preview,
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
            preview=data["preview"],
            smart_title_generated=data.get("smart_title_generated", False),
        )


@dataclass
class Chat:
    """A chat session with messages and metadata."""

    metadata: ChatMetadata
    messages: List[Dict[str, str]] = field(default_factory=list)

    @property
    def chat_dir(self) -> Path:
        """Get the directory for this chat."""
        config = Config()
        return Path(config.chat_dir) / self.metadata.id

    def should_be_saved(self) -> bool:
        """Check if chat should be saved (has non-system messages)."""
        return len([m for m in self.messages if m["role"] != "system"]) > 0

    def save(self) -> None:
        """Save chat to disk only if it has non-system messages."""
        if not self.should_be_saved():
            return
            
        chat_dir = self.chat_dir
        chat_dir.mkdir(parents=True, exist_ok=True)

        # Update metadata
        self.metadata.updated_at = datetime.now()
        self.metadata.message_count = len(
            [m for m in self.messages if m["role"] != "system"]
        )

        # Track if we've generated smart title to avoid regenerating
        if not hasattr(self.metadata, "smart_title_generated"):
            self.metadata.smart_title_generated = False

        # Save metadata
        with open(chat_dir / "metadata.json", "w") as f:
            json.dump(self.metadata.to_dict(), f, indent=2)

        # Save messages
        with open(chat_dir / "messages.json", "w") as f:
            json.dump(self.messages, f, indent=2)

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
            messages = json.load(f)

        return cls(metadata=metadata, messages=messages)