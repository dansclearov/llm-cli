"""Chat management with auto-save and smart title generation."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from llm_cli.config.settings import Config
from llm_cli.constants import MAX_TITLE_LENGTH
from llm_cli.core.message_utils import build_prompt, flatten_history, response_text
from llm_cli.core.session import Chat, ChatMetadata
from llm_cli.llm_types import ChatOptions
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
        )

        chat = Chat(metadata=metadata)
        chat.pending_system_prompt = system_message
        # Don't save empty chats - they'll be saved when first message is added
        return chat

    def list_chats(self) -> List[ChatMetadata]:
        """List all available chats, sorted by updated_at desc."""
        chat_dir = Path(self.config.chat_dir)
        if not chat_dir.exists():
            return []

        chats = []
        try:
            chat_folders = list(chat_dir.iterdir())
        except OSError as exc:
            self.console.print(
                f"[dim]Unable to read chat directory {chat_dir}: {exc}[/dim]"
            )
            return []

        for chat_folder in chat_folders:
            if chat_folder.is_dir():
                try:
                    metadata_file = chat_folder / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, "r") as f:
                            metadata = ChatMetadata.from_dict(json.load(f))
                            chats.append(metadata)
                except (
                    OSError,
                    json.JSONDecodeError,
                    KeyError,
                    TypeError,
                    ValueError,
                ) as exc:
                    self.console.print(
                        "[dim]Skipping unreadable chat metadata in "
                        f"{chat_folder.name}: {type(exc).__name__}[/dim]"
                    )
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
        flattened_history = flatten_history(chat.messages)
        if not flattened_history:
            return

        try:
            # Take first few exchanges for title generation
            conversation_sample = []
            for role, content in flattened_history[:8]:
                prefix = "User" if role == "user" else "Assistant"
                conversation_sample.append(f"{prefix}: {content}")

            conversation_text = "\n".join(conversation_sample)

            # Generate title using LLM (single-turn prompt)
            title_prompt = build_prompt(
                "Generate a concise 5-10 word title for this conversation. "
                "No quotes, no punctuation, just the title.",
                f"Conversation:\n{conversation_text}\n\nTitle:",
            )

            options = ChatOptions(
                enable_search=False,
                enable_thinking=False,
                show_thinking=False,
                silent=True,
            )

            response = llm_client.chat(title_prompt, model, options)
            new_title = response_text(response).strip()

            # Clean up the title (remove quotes, limit length)
            new_title = new_title.strip("\"'").strip()
            if len(new_title) > MAX_TITLE_LENGTH:
                new_title = new_title[: MAX_TITLE_LENGTH - 3] + "..."

            if new_title and new_title != chat.metadata.title:
                chat.metadata.title = new_title

            self._mark_title_generation_attempted(chat)
        except KeyboardInterrupt:
            raise
        except (OSError, RuntimeError, TimeoutError, TypeError, ValueError) as exc:
            self.console.print(
                f"[dim]Smart title generation skipped: {type(exc).__name__}[/dim]"
            )
            self._mark_title_generation_attempted(chat)

    def _mark_title_generation_attempted(self, chat: Chat) -> None:
        """Persist that smart-title generation has been attempted."""
        chat.metadata.smart_title_generated = True
        try:
            chat.save()
        except OSError as exc:
            self.console.print(
                f"[dim]Could not persist smart-title status: {type(exc).__name__}[/dim]"
            )
