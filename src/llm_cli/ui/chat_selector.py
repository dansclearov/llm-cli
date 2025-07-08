"""Interactive chat selection UI."""

import sys
import termios
import tty
from typing import List, Optional

from rich.console import Console
from rich.live import Live

from llm_cli.constants import (
    DEFAULT_PAGE_SIZE,
    INITIAL_PAGE,
    INITIAL_SELECTED_INDEX,
    NAVIGATION_KEYS,
)
from llm_cli.core.session import Chat, ChatMetadata
from llm_cli.exceptions import ChatNotFoundError


class ChatSelector:
    """Interactive chat selection with keyboard navigation."""

    def __init__(self, console: Console):
        self.console = console

    def select_chat(self, chats: List[ChatMetadata]) -> Optional[Chat]:
        """Interactive chat selection with keyboard navigation."""
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

                    if key in NAVIGATION_KEYS["UP"]:
                        if selected_index > 0:
                            selected_index -= 1
                        elif current_page > 0:
                            current_page -= 1
                            selected_index = min(
                                len(get_current_page_chats()) - 1, page_size - 1
                            )

                    elif key in NAVIGATION_KEYS["DOWN"]:
                        if selected_index < len(page_chats) - 1:
                            selected_index += 1
                        elif current_page < total_pages - 1:
                            current_page += 1
                            selected_index = INITIAL_SELECTED_INDEX

                    elif key in NAVIGATION_KEYS["ENTER"]:
                        selected_chat = page_chats[selected_index]
                        return Chat.load(selected_chat.id)

                    elif (
                        key in NAVIGATION_KEYS["NEXT_PAGE"] and current_page < total_pages - 1
                    ):
                        current_page += 1
                        selected_index = INITIAL_SELECTED_INDEX

                    elif (
                        key in NAVIGATION_KEYS["PREV_PAGE"] and current_page > 0
                    ):
                        current_page -= 1
                        selected_index = INITIAL_SELECTED_INDEX

                    elif key == NAVIGATION_KEYS["DELETE"]:
                        # Wait for second 'd'
                        second_key = get_key()
                        if second_key == NAVIGATION_KEYS["DELETE"]:
                            # Delete the selected chat
                            selected_chat = page_chats[selected_index]
                            self._delete_chat(selected_chat.id)
                            # Refresh chat list and adjust selection
                            chats = self._refresh_chat_list(chats, selected_chat.id)
                            if not chats:
                                return None
                            total_pages = (len(chats) + page_size - 1) // page_size
                            if current_page >= total_pages:
                                current_page = max(0, total_pages - 1)
                            page_chats = get_current_page_chats()
                            if selected_index >= len(page_chats) and page_chats:
                                selected_index = len(page_chats) - 1

                    elif key in NAVIGATION_KEYS["QUIT"]:
                        return None

                    # Update the display
                    live.update(render_selection())

        except KeyboardInterrupt:
            return None

    def _delete_chat(self, chat_id: str) -> None:
        """Delete a chat by moving it to trash."""
        try:
            import send2trash
            from pathlib import Path
            from llm_cli.config.settings import Config

            config = Config()
            chat_dir = Path(config.chat_dir) / chat_id
            if chat_dir.exists():
                send2trash.send2trash(str(chat_dir))
        except ImportError:
            # Fallback to regular deletion if send2trash not available
            import shutil
            from pathlib import Path
            from llm_cli.config.settings import Config

            config = Config()
            chat_dir = Path(config.chat_dir) / chat_id
            if chat_dir.exists():
                shutil.rmtree(chat_dir)

    def _refresh_chat_list(self, chats: List[ChatMetadata], deleted_id: str) -> List[ChatMetadata]:
        """Remove deleted chat from the list."""
        return [chat for chat in chats if chat.id != deleted_id]