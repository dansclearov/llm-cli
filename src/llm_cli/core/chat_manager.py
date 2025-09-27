"""Chat management with auto-save and smart title generation."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from llm_cli.config.settings import Config
from llm_cli.constants import MAX_TITLE_LENGTH
from llm_cli.core.session import Chat, ChatMetadata
from llm_cli.providers.base import ChatOptions
from llm_cli.ui.chat_selector import ChatSelector


class ChatManager:
    """Manages chat sessions with auto-save and interactive selection."""

    def __init__(self, config: Config):
        self.config = config
        # Disable Rich's automatic syntax highlighting - it makes timestamps look like code
        self.console = Console(highlight=False)
        self.chat_selector = ChatSelector(self.console)

    def create_new_chat(self, model: str, system_message: str) -> Chat:
        """Create a new empty chat session."""
        chat_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        metadata = ChatMetadata(
            id=chat_id,
            title=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            model=model,
            message_count=0,
            preview="New chat",
        )

        messages = [{"role": "system", "content": system_message}]
        chat = Chat(metadata=metadata, messages=messages)
        # Don't save empty chats - they'll be saved when first message is added
        return chat

    def list_chats(self) -> List[ChatMetadata]:
        """List all available chats, sorted by updated_at desc."""
        chat_dir = Path(self.config.chat_dir)
        if not chat_dir.exists():
            return []

        chats = []
        for chat_folder in chat_dir.iterdir():
            if chat_folder.is_dir():
                try:
                    metadata_file = chat_folder / "metadata.json"
                    if metadata_file.exists():
                        import json

                        with open(metadata_file, "r") as f:
                            metadata = ChatMetadata.from_dict(json.load(f))
                            chats.append(metadata)
                except Exception:
                    # Skip corrupted chat folders
                    continue

        # Sort by updated_at descending
        return sorted(chats, key=lambda c: c.updated_at, reverse=True)

    def get_last_chat(self) -> Optional[Chat]:
        """Get the most recently updated chat."""
        chats = self.list_chats()
        if chats:
            return Chat.load(chats[0].id)  # First item is most recent
        return None

    def interactive_chat_selection(self) -> Optional[Chat]:
        """Interactive chat selection with keyboard navigation."""
        chats = self.list_chats()
        return self.chat_selector.select_chat(chats)

    def generate_smart_title(self, chat: Chat, llm_client, model: str) -> None:
        """Generate a better title using LLM for chats with >3 message pairs."""
        # Caller should check smart_title_generated flag
        non_system_messages = [msg for msg in chat.messages if msg["role"] != "system"]

        try:
            # Take first few exchanges for title generation
            conversation_sample = []
            for i in range(0, min(8, len(non_system_messages)), 2):  # First 5 pairs max
                if i < len(non_system_messages):
                    conversation_sample.append(
                        f"User: {non_system_messages[i]['content']}"
                    )
                if i + 1 < len(non_system_messages):
                    conversation_sample.append(
                        f"Assistant: {non_system_messages[i + 1]['content']}"
                    )

            conversation_text = "\n".join(conversation_sample)

            # Generate title using LLM
            title_prompt = [
                {
                    "role": "system",
                    "content": "Generate a concise 5-10 word title for this conversation. No quotes, no punctuation, just the title.",
                },
                {
                    "role": "user",
                    "content": f"Conversation:\n{conversation_text}\n\nTitle:",
                },
            ]

            options = ChatOptions(
                enable_search=False,
                enable_thinking=False,
                show_thinking=False,
                silent=True,
            )

            new_title = llm_client.chat(title_prompt, model, options).strip()

            # Clean up the title (remove quotes, limit length)
            new_title = new_title.strip("\"'").strip()
            if len(new_title) > MAX_TITLE_LENGTH:
                new_title = new_title[: MAX_TITLE_LENGTH - 3] + "..."

            if new_title and new_title != chat.metadata.title:
                chat.metadata.title = new_title

            # Mark as generated regardless of success/failure
            chat.metadata.smart_title_generated = True
            chat.save()

        except Exception:
            # If title generation fails, mark as attempted so we don't retry
            chat.metadata.smart_title_generated = True
            chat.save()
