"""Main application orchestration."""

import sys
from typing import Dict, List, Optional

from dotenv import load_dotenv

from llm_cli.cli import parse_arguments
from llm_cli.config.settings import Config, setup_providers
from llm_cli.constants import (
    AI_COLOR,
    AI_PROMPT,
    MIN_MESSAGES_FOR_SMART_TITLE,
    RESET_COLOR,
    SYSTEM_COLOR,
    USER_COLOR,
    USER_PROMPT,
)
from llm_cli.core.chat_manager import ChatManager
from llm_cli.core.client import LLMClient
from llm_cli.core.session import Chat
from llm_cli.prompts import read_system_message_from_file
from llm_cli.providers.base import ChatOptions
from llm_cli.ui.input_handler import InputHandler

load_dotenv()


def print_all_messages(messages: List[Dict[str, str]]) -> None:
    """Print all messages in the conversation history."""
    for msg in messages:
        if msg["role"] == "system":
            continue

        role_label = USER_PROMPT if msg["role"] == "user" else AI_PROMPT
        role_color = USER_COLOR if msg["role"] == "user" else AI_COLOR
        print(f"{role_color}{role_label}{RESET_COLOR}{msg['content']}")


def setup_configuration(
    args,
) -> tuple[Config, ChatManager, LLMClient, InputHandler, ChatOptions, str]:
    """Set up configuration and components."""
    config = Config()
    chat_manager = ChatManager(config)
    llm_client = LLMClient()
    input_handler = InputHandler()

    # Set up chat options
    chat_options = ChatOptions(
        enable_search=args.search,
        enable_thinking=args.thinking,
        show_thinking=not args.hide_thinking,
    )

    prompt_str = read_system_message_from_file("prompt_" + args.prompt + ".txt")

    return config, chat_manager, llm_client, input_handler, chat_options, prompt_str


def handle_chat_selection(args, chat_manager: ChatManager) -> Optional[Chat]:
    """Handle chat selection/loading based on arguments."""
    current_chat: Optional[Chat] = None

    if args.resume is not None:
        if args.resume:  # Specific chat ID provided
            try:
                current_chat = Chat.load(args.resume)
                print(f"Loaded chat: {current_chat.metadata.title}")
            except FileNotFoundError:
                print(f"Chat not found: {args.resume}")
                return None
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


def create_new_chat(
    args,
    chat_manager: ChatManager,
    input_handler: InputHandler,
    llm_client: LLMClient,
    prompt_str: str,
    chat_options: ChatOptions,
) -> Optional[Chat]:
    """Create a new chat session."""
    print(
        f"Starting new {args.model} chat session. "
        "Press Ctrl+C to exit. Use Shift+Enter for new lines."
    )
    print(f"{SYSTEM_COLOR}System:{RESET_COLOR} {prompt_str}")

    # Get first user message to create chat
    try:
        first_message = input_handler.get_user_input()
    except KeyboardInterrupt:
        return None

    current_chat = chat_manager.create_new_chat(args.model, prompt_str, first_message)

    # Process first message immediately
    response = llm_client.chat(current_chat.messages, args.model, chat_options)
    current_chat.messages.append({"role": "assistant", "content": response})
    current_chat.save()

    return current_chat


def run_chat_loop(
    current_chat: Chat,
    args,
    chat_manager: ChatManager,
    llm_client: LLMClient,
    input_handler: InputHandler,
    chat_options: ChatOptions,
    prompt_str: str,
    is_new_chat: bool = False,
) -> None:
    """Run the main chat interaction loop."""
    # Only show initial display for existing chats
    if not is_new_chat:
        # Show system message if different from current prompt
        system_message = next(
            (msg["content"] for msg in current_chat.messages if msg["role"] == "system"),
            "",
        )
        if system_message != prompt_str:
            print(f"{SYSTEM_COLOR}System (from chat):{RESET_COLOR} {system_message}")
        else:
            print(f"{SYSTEM_COLOR}System:{RESET_COLOR} {prompt_str}")

        print_all_messages(current_chat.messages)

    # Main interaction loop
    finished = True
    while True:
        try:
            user_input = input_handler.get_user_input()

            # Process normal input
            current_chat.messages.append({"role": "user", "content": user_input})

            finished = False
            response = llm_client.chat(current_chat.messages, args.model, chat_options)
            current_chat.messages.append({"role": "assistant", "content": response})
            current_chat.save()  # Auto-save after each exchange

            # Generate smart title once we have enough conversation (only once per chat)
            non_system_count = len(
                [m for m in current_chat.messages if m["role"] != "system"]
            )
            should_generate_title = (
                non_system_count >= MIN_MESSAGES_FOR_SMART_TITLE
                and not current_chat.metadata.smart_title_generated
            )
            if should_generate_title:
                chat_manager.generate_smart_title(current_chat, llm_client, args.model)

            finished = True

        except KeyboardInterrupt:
            if not finished:
                finished = True
                print("", flush=True)
            else:
                current_chat.save()  # Final save before exit
                break


def main():
    """Main entry point for the LLM CLI application."""
    registry = setup_providers()
    args = parse_arguments(registry)
    config, chat_manager, llm_client, input_handler, chat_options, prompt_str = (
        setup_configuration(args)
    )

    # Handle chat selection/loading
    current_chat = handle_chat_selection(args, chat_manager)
    is_new_chat = False

    if current_chat is None:
        # Create new chat
        current_chat = create_new_chat(
            args, chat_manager, input_handler, llm_client, prompt_str, chat_options
        )
        if current_chat is None:  # User cancelled during creation
            return
        is_new_chat = True

    # Show continuation message for existing chats
    if not is_new_chat and current_chat.metadata.message_count > 2:
        print(
            f"Continuing chat: {current_chat.metadata.title} "
            f"({current_chat.metadata.model}, {current_chat.metadata.message_count} messages)"
        )
        print("Press Ctrl+C to exit. Use Shift+Enter for new lines.")

    run_chat_loop(
        current_chat,
        args,
        chat_manager,
        llm_client,
        input_handler,
        chat_options,
        prompt_str,
        is_new_chat,
    )


if __name__ == "__main__":
    main()
