"""Chat management with auto-save and interactive selection."""

import json
import sys
import termios
import tty
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.live import Live
from rich.prompt import Prompt
from rich.table import Table
from rich.theme import Theme

from .config import Config

# Constants
DEFAULT_PAGE_SIZE = 10
INITIAL_PAGE = 0
INITIAL_SELECTED_INDEX = 0


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

    def save(self) -> None:
        """Save chat to disk."""
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
            raise FileNotFoundError(f"Chat not found: {chat_id}")

        # Load metadata
        with open(chat_dir / "metadata.json", "r") as f:
            metadata = ChatMetadata.from_dict(json.load(f))

        # Load messages
        with open(chat_dir / "messages.json", "r") as f:
            messages = json.load(f)

        return cls(metadata=metadata, messages=messages)


class ChatManager:
    """Manages chat sessions with auto-save and interactive selection."""

    def __init__(self, config: Config):
        self.config = config
        # Disable Rich's automatic syntax highlighting - it makes timestamps look like code
        self.console = Console(highlight=False)

    def create_new_chat(
        self, model: str, system_message: str, first_user_message: str = ""
    ) -> Chat:
        """Create a new chat session."""
        chat_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        # Generate title from first user message
        title = self._generate_title(first_user_message)
        preview = (
            (first_user_message[:50] + "...")
            if len(first_user_message) > 50
            else first_user_message
        )

        metadata = ChatMetadata(
            id=chat_id,
            title=title,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            model=model,
            message_count=0,
            preview=preview or "New chat",
        )

        messages = [{"role": "system", "content": system_message}]
        if first_user_message:
            messages.append({"role": "user", "content": first_user_message})

        chat = Chat(metadata=metadata, messages=messages)
        chat.save()
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

        if not chats:
            self.console.print("No existing chats found.")
            return None

        page_size = DEFAULT_PAGE_SIZE
        current_page = INITIAL_PAGE
        selected_index = INITIAL_SELECTED_INDEX
        total_pages = (len(chats) + page_size - 1) // page_size

        def get_current_page_chats():
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(chats))
            return chats[start_idx:end_idx]

        def render_selection():
            page_chats = get_current_page_chats()
            output = []

            output.append(
                f"Select a chat to continue ({current_page + 1}/{total_pages}):"
            )
            output.append("")

            for i, chat in enumerate(page_chats):
                date_str = chat.updated_at.strftime("%Y-%m-%d %H:%M")
                title = chat.title[:50] + "..." if len(chat.title) > 50 else chat.title

                if i == selected_index:
                    # Highlighted selection
                    output.append(
                        f"[bright_yellow]❯ {i+1}. [{date_str}] {title:<52} "
                        f"[bright_black]({chat.model}, {chat.message_count} msgs)[/bright_black][/bright_yellow]"
                    )
                else:
                    # Normal entry
                    output.append(
                        f"  {i+1}. [{date_str}] {title:<52} "
                        f"[bright_black]({chat.model}, {chat.message_count} msgs)[/bright_black]"
                    )

            if total_pages > 1:
                output.append("")
                output.append(
                    f"[dim]↑/↓/k/j or Ctrl+P/N: navigate, Enter: select, n/p or Ctrl+L/H: pages, dd: delete, q: quit[/dim]"
                )
            else:
                output.append("")
                output.append(
                    f"[dim]↑/↓/k/j or Ctrl+P/N: navigate, Enter: select, dd: delete, q: quit[/dim]"
                )

            return "\n".join(output)

        def get_key():
            """Get a single keypress."""
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                key = sys.stdin.read(1)

                # Handle escape sequences (arrow keys)
                if key == "\x1b":
                    key += sys.stdin.read(2)

                return key
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        try:
            with Live(
                render_selection(), console=self.console, refresh_per_second=10
            ) as live:
                while True:
                    page_chats = get_current_page_chats()
                    key = get_key()

                    if key in ["\x1b[A", "\x10", "k"]:  # Up arrow, Ctrl+P, or k
                        if selected_index > 0:
                            selected_index -= 1
                        elif current_page > 0:
                            current_page -= 1
                            selected_index = min(
                                len(get_current_page_chats()) - 1, page_size - 1
                            )

                    elif key in ["\x1b[B", "\x0e", "j"]:  # Down arrow, Ctrl+N, or j
                        if selected_index < len(page_chats) - 1:
                            selected_index += 1
                        elif current_page < total_pages - 1:
                            current_page += 1
                            selected_index = INITIAL_SELECTED_INDEX

                    elif key == "\r" or key == "\n":  # Enter
                        selected_chat = page_chats[selected_index]
                        return Chat.load(selected_chat.id)

                    elif (
                        key in ["n", "\x0c"] and current_page < total_pages - 1
                    ):  # n or Ctrl+L (next page)
                        current_page += 1
                        selected_index = INITIAL_SELECTED_INDEX

                    elif (
                        key in ["p", "\x08"] and current_page > 0
                    ):  # p or Ctrl+H (previous page)
                        current_page -= 1
                        selected_index = INITIAL_SELECTED_INDEX

                    elif key == "d":  # First 'd' for delete
                        # Wait for second 'd'
                        second_key = get_key()
                        if second_key == "d":
                            # Delete the selected chat
                            selected_chat = page_chats[selected_index]
                            self._delete_chat(selected_chat.id)
                            # Refresh chat list and adjust selection
                            chats = self.list_chats()
                            if not chats:
                                return None
                            total_pages = (len(chats) + page_size - 1) // page_size
                            if current_page >= total_pages:
                                current_page = max(0, total_pages - 1)
                            page_chats = get_current_page_chats()
                            if selected_index >= len(page_chats) and page_chats:
                                selected_index = len(page_chats) - 1

                    elif key == "q" or key == "\x03":  # q or Ctrl+C
                        return None

                    # Update the display
                    live.update(render_selection())

        except KeyboardInterrupt:
            return None

    def _delete_chat(self, chat_id: str) -> None:
        """Delete a chat by moving it to trash."""
        import send2trash

        chat_dir = Path(self.config.chat_dir) / chat_id
        if chat_dir.exists():
            send2trash.send2trash(str(chat_dir))

    def _display_chat_table(
        self, chats: List[ChatMetadata], page: int, total_pages: int
    ) -> None:
        """Display a simple list of chats."""
        self.console.print(f"Select a chat to continue (Page {page}/{total_pages}):")

        for i, chat in enumerate(chats, 1):
            date_str = chat.updated_at.strftime("%Y-%m-%d %H:%M")
            # Truncate title if too long
            title = chat.title[:50] + "..." if len(chat.title) > 50 else chat.title

            self.console.print(
                f"  {i:2}. "
                f"[{date_str}] "
                f"{title:<52} "
                f"[bright_black]({chat.model}, {chat.message_count} msgs)[/bright_black]"
            )

        if total_pages > 1:
            self.console.print(f"\n{' ' * 60}[Page {page}/{total_pages}]")

    def _generate_title(self, first_message: str) -> str:
        """Generate a chat title from the first user message."""
        if not first_message:
            return f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Take first 40 chars, remove newlines, clean up
        title = first_message.replace("\n", " ").strip()[:40]
        if len(first_message) > 40:
            title += "..."

        return title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"

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
                        f"Human: {non_system_messages[i]['content']}"
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
                    "content": "Generate a very concise 3-7 word title for this conversation. No quotes, no punctuation, just the title.",
                },
                {
                    "role": "user",
                    "content": f"Conversation:\n{conversation_text}\n\nTitle:",
                },
            ]

            from .providers.base import ChatOptions

            options = ChatOptions(
                enable_search=False,
                enable_thinking=False,
                show_thinking=False,
                silent=True,
            )

            new_title = llm_client.chat(title_prompt, model, options).strip()

            # Clean up the title (remove quotes, limit length)
            new_title = new_title.strip("\"'").strip()
            if len(new_title) > 60:
                new_title = new_title[:57] + "..."

            if new_title and new_title != chat.metadata.title:
                chat.metadata.title = new_title

            # Mark as generated regardless of success/failure
            chat.metadata.smart_title_generated = True
            chat.save()

        except Exception:
            # If title generation fails, mark as attempted so we don't retry
            chat.metadata.smart_title_generated = True
            chat.save()
