"""Main application orchestration."""

import os
import sys
from pathlib import Path
from typing import Optional, Sequence

from dotenv import load_dotenv
from platformdirs import user_config_dir, user_data_dir

from llm_cli.cli import parse_arguments
from llm_cli.config.settings import Config, setup_providers
from llm_cli.config.user_config import update_user_config
from llm_cli.constants import (
    AI_COLOR,
    AI_PROMPT,
    MAX_TITLE_LENGTH,
    MIN_MESSAGES_FOR_SMART_TITLE,
    RESET_COLOR,
    SYSTEM_COLOR,
    USER_COLOR,
    USER_PROMPT,
)
from pydantic_ai.messages import ModelMessage, ModelRequest

from llm_cli.core.chat_manager import ChatManager
from llm_cli.core.client import LLMClient
from llm_cli.core.message_utils import (
    count_non_system_messages,
    flatten_history,
    latest_system_prompt,
)
from llm_cli.core.session import Chat
from llm_cli.exceptions import (
    ChatNotFoundError,
    ModelNotFoundError,
    PromptNotFoundError,
)
from llm_cli.prompts import read_system_message_from_file
from llm_cli.llm_types import ChatOptions
from llm_cli.ui.input_handler import InputHandler

load_dotenv()


def print_user_paths() -> None:
    """Print all user path locations used by the application."""
    config_dir = Path(user_config_dir("llm_cli", ensure_exists=True))
    data_dir = Path(user_data_dir("llm_cli", ensure_exists=True))

    # Configuration directory
    print(f"Configuration directory: {config_dir}")
    print(f"  - User config file: {config_dir / 'config.json'}")
    print(f"  - User prompts: {config_dir / 'prompts'}/ (*.txt files)")
    print(f"  - User model overrides: {config_dir / 'models.yaml'}")

    # Data directory
    chat_dir = os.getenv("LLM_CLI_CHAT_DIR", str(data_dir / "chats"))
    print(f"Data directory: {data_dir}")
    print(f"  - Chat storage: {chat_dir}")

    # Environment variable overrides
    print("\nEnvironment variable overrides:")
    print(f"  - LLM_CLI_CHAT_DIR: {os.getenv('LLM_CLI_CHAT_DIR', 'not set')}")

    # Show which paths currently exist
    print("\nCurrent status:")
    paths_to_check = [
        config_dir,
        config_dir / "config.json",
        config_dir / "prompts",
        config_dir / "models.yaml",
        Path(chat_dir),
    ]

    for path in paths_to_check:
        exists = "✓" if path.exists() else "✗"
        print(f"  {exists} {path}")


def print_all_messages(messages: Sequence[ModelMessage]) -> None:
    """Print all messages in the conversation history."""
    for role, content in flatten_history(messages):
        role_label = USER_PROMPT if role == "user" else AI_PROMPT
        role_color = USER_COLOR if role == "user" else AI_COLOR
        print(f"{role_color}{role_label}{RESET_COLOR}{content}")


def setup_configuration(
    args, registry
) -> tuple[Config, ChatManager, LLMClient, InputHandler, ChatOptions, str]:
    """Set up configuration and components."""
    config = Config()
    chat_manager = ChatManager(config)
    llm_client = LLMClient(registry)
    input_handler = InputHandler(config)

    # Set up chat options
    chat_options = ChatOptions(
        enable_search=args.search,
        enable_thinking=not args.no_thinking,
        show_thinking=not args.no_thinking and not args.hide_thinking,
    )

    prompt_str = read_system_message_from_file("prompt_" + args.prompt + ".txt")

    return config, chat_manager, llm_client, input_handler, chat_options, prompt_str


def handle_chat_selection(args, chat_manager: ChatManager) -> Optional[Chat]:
    """Handle chat selection/loading based on arguments."""
    current_chat: Optional[Chat] = None

    if args.resume is not None:
        if args.resume:  # Specific chat ID provided
            try:
                current_chat = chat_manager.load_chat(args.resume)
                print(f"Loaded chat: {current_chat.metadata.title}")
            except (ChatNotFoundError, FileNotFoundError):
                print(f"Chat not found: {args.resume}")
                sys.exit(1)
        else:  # No ID provided, show selector
            current_chat = chat_manager.interactive_chat_selection()
            if current_chat is None:
                # User cancelled, exit
                sys.exit(0)
    elif getattr(args, "continue"):
        # Continue most recent chat
        current_chat = chat_manager.get_last_chat()
        if not current_chat:
            print("No previous chats found. Starting new chat...")

    return current_chat


def _print_chat_session_context(current_chat: Chat, prompt_str: str) -> None:
    """Print startup context for new or resumed chats."""
    history = flatten_history(current_chat.messages)
    has_user_messages = any(role == "user" for role, _ in history)

    if not has_user_messages:
        print(
            f"Starting new {current_chat.metadata.model} chat session. "
            "Press Ctrl+C to exit. Use Shift+Enter for new lines."
        )
        print(f"{SYSTEM_COLOR}System:{RESET_COLOR} {prompt_str}")
        return

    system_message = latest_system_prompt(current_chat.messages) or ""
    if system_message != prompt_str:
        print(f"{SYSTEM_COLOR}System (from chat):{RESET_COLOR} {system_message}")
    else:
        print(f"{SYSTEM_COLOR}System:{RESET_COLOR} {prompt_str}")

    print_all_messages(current_chat.messages)


def _handle_local_command(normalized_input: str, config: Config) -> bool:
    """Handle local slash commands. Returns True when handled."""
    if not normalized_input.startswith("/vim"):
        return False

    config.vim_mode = not config.vim_mode
    update_user_config("vim_mode", config.vim_mode)
    return True


def _update_title_from_first_user_message(current_chat: Chat) -> None:
    """Replace placeholder title with the first user message."""
    if not current_chat.metadata.title.startswith("Chat "):
        return

    user_messages = [
        content
        for role, content in flatten_history(current_chat.messages)
        if role == "user"
    ]
    if len(user_messages) != 1:
        return

    first_msg = user_messages[0]
    current_chat.metadata.title = first_msg.replace("\n", " ").strip()[
        :MAX_TITLE_LENGTH
    ]


def _maybe_generate_smart_title(
    current_chat: Chat,
    chat_manager: ChatManager,
    llm_client: LLMClient,
    active_model: str,
) -> None:
    """Generate a smart title once enough conversation exists."""
    non_system_count = count_non_system_messages(current_chat.messages)
    should_generate_title = (
        non_system_count >= MIN_MESSAGES_FOR_SMART_TITLE
        and not current_chat.metadata.smart_title_generated
    )
    if should_generate_title:
        chat_manager.generate_smart_title(current_chat, llm_client, active_model)


def run_chat_loop(
    current_chat: Chat,
    chat_manager: ChatManager,
    llm_client: LLMClient,
    input_handler: InputHandler,
    chat_options: ChatOptions,
    prompt_str: str,
    config: Config,
    active_model: str,
) -> None:
    """Run the main chat interaction loop."""
    _print_chat_session_context(current_chat, prompt_str)
    capabilities_override = current_chat.metadata.get_model_capabilities_snapshot()

    # Main interaction loop
    finished = True
    while True:
        pending_user_message = False
        try:
            user_input = input_handler.get_user_input()
            normalized_input = user_input.strip()

            if not normalized_input:
                continue

            if _handle_local_command(normalized_input, config):
                continue

            # Process normal input
            current_chat.append_user_message(user_input)
            pending_user_message = True

            finished = False
            try:
                model_response = llm_client.chat(
                    current_chat.messages,
                    active_model,
                    chat_options,
                    capabilities_override=capabilities_override,
                )
            except KeyboardInterrupt:
                _discard_pending_user_message(current_chat)
                pending_user_message = False
                raise
            except Exception as exc:
                _discard_pending_user_message(current_chat)
                pending_user_message = False
                finished = True
                print(f"Request failed: {type(exc).__name__}: {exc}")
                continue

            current_chat.append_assistant_response(model_response)
            pending_user_message = False

            _update_title_from_first_user_message(current_chat)

            chat_manager.save_chat(current_chat)  # Auto-save after each exchange

            _maybe_generate_smart_title(
                current_chat, chat_manager, llm_client, active_model
            )

            finished = True

        except KeyboardInterrupt:
            if not finished:
                if pending_user_message:
                    _discard_pending_user_message(current_chat)
                finished = True
                print("", flush=True)
            else:
                chat_manager.save_chat(current_chat)  # Final save before exit
                break


def _discard_pending_user_message(current_chat: Chat) -> None:
    """Drop a trailing user request when generation fails or is interrupted."""
    if not current_chat.messages:
        return

    if isinstance(current_chat.messages[-1], ModelRequest):
        current_chat.messages.pop()


def main():
    """Main entry point for the LLM CLI application."""
    registry = setup_providers()
    args = parse_arguments(registry)

    # Handle --user-paths command
    if args.user_paths:
        print_user_paths()
        return

    try:
        config, chat_manager, llm_client, input_handler, chat_options, prompt_str = (
            setup_configuration(args, registry)
        )
    except PromptNotFoundError as e:
        print(e)
        sys.exit(2)

    # Handle chat selection/loading
    current_chat = handle_chat_selection(args, chat_manager)
    is_new_chat = False
    requested_model = registry.resolve_model_name(args.model)

    if current_chat is None:
        # Create new chat
        current_chat = chat_manager.create_new_chat(requested_model, prompt_str)
        current_chat.metadata.set_model_capabilities_snapshot(
            registry.get_model_capabilities(requested_model)
        )
        is_new_chat = True
    active_model = current_chat.metadata.model
    if not is_new_chat:
        try:
            active_model_for_comparison = registry.resolve_model_name(active_model)
        except ModelNotFoundError:
            active_model_for_comparison = active_model
    else:
        active_model_for_comparison = active_model
    if not is_new_chat and requested_model != active_model_for_comparison:
        print(
            f"Resumed chat locked to its original model: {active_model} "
            f"(ignoring --model {args.model})"
        )

    # Show continuation message for existing chats
    if not is_new_chat and current_chat.metadata.message_count > 2:
        print(
            f"Continuing chat: {current_chat.metadata.title} "
            f"({current_chat.metadata.model}, {current_chat.metadata.message_count} messages)"
        )
        print("Press Ctrl+C to exit. Use Shift+Enter for new lines.")

    run_chat_loop(
        current_chat,
        chat_manager,
        llm_client,
        input_handler,
        chat_options,
        prompt_str,
        config,
        active_model,
    )


if __name__ == "__main__":
    main()
