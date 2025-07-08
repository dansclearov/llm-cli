import argparse
import signal
import sys
from typing import Dict, List, Optional

from colored import attr, fg
from dotenv import load_dotenv
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from tenacity import retry, stop_after_attempt, wait_exponential

from llm_cli.chat_manager import Chat, ChatManager
from llm_cli.config import Config, setup_providers
from llm_cli.constants import AI_PROMPT, MESSAGES_PER_HISTORY_PAIR, MIN_MESSAGES_FOR_SMART_TITLE, USER_PROMPT
from llm_cli.providers.base import ChatOptions
from llm_cli.response_handler import ResponseHandler
from llm_cli.utils import read_system_message_from_file

load_dotenv()

USER_COLOR = fg("green") + attr("bold")
AI_COLOR = fg("blue") + attr("bold")
SYSTEM_COLOR = fg("violet") + attr("bold")
RESET_COLOR = attr("reset")



def print_all_messages(messages: List[Dict[str, str]]) -> None:
    """Print all messages in the conversation history."""
    for msg in messages:
        if msg["role"] == "system":
            continue

        role_label = USER_PROMPT if msg["role"] == "user" else AI_PROMPT
        role_color = USER_COLOR if msg["role"] == "user" else AI_COLOR
        print(f"{role_color}{role_label}{RESET_COLOR}{msg['content']}")


class LLMClient:
    def __init__(self):
        self.registry = setup_providers()
        self.interrupt_handler = None

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def chat(
        self,
        messages: List[Dict[str, str]],
        model_alias: str,
        options: ChatOptions = None,
    ) -> str:
        """Get response from the specified model."""
        if options is None:
            options = ChatOptions()

        try:
            provider, model_id = self.registry.get_provider_for_model(model_alias)
            capabilities = provider.get_capabilities(model_id)

            # Validate options against capabilities
            if options.enable_search and not capabilities.supports_search:
                print(f"Warning: {model_alias} doesn't support search.")
                options.enable_search = False

            # Set up response handler
            handler = ResponseHandler(capabilities, options, use_styled_output=True)
            self.interrupt_handler = handler

            # Set up signal handler for interrupt during streaming
            def handle_interrupt(signum, frame):
                if self.interrupt_handler:
                    self.interrupt_handler.mark_interrupted()
                    raise KeyboardInterrupt()

            old_handler = signal.signal(signal.SIGINT, handle_interrupt)

            try:
                # Stream response
                handler.start_response()
                for chunk in provider.stream_response(messages, model_id, options):
                    handler.handle_chunk(chunk)
                handler.finish_response()
            except KeyboardInterrupt:
                # Handle interrupt gracefully during streaming
                handler.finish_response()
            finally:
                # Restore original signal handler
                signal.signal(signal.SIGINT, old_handler)
                self.interrupt_handler = None

            return handler.get_full_response()

        except Exception as e:
            # Re-raise to let tenacity handle retries
            raise e


class InputHandler:
    @staticmethod
    def get_user_input() -> str:
        """Get user input with shift+enter for new lines."""
        bindings = KeyBindings()
        
        @bindings.add('c-m')  # Enter key
        def _(event):
            # Submit the input
            event.app.exit(result=event.app.current_buffer.text)
        
        @bindings.add('c-j')  # Ctrl+J / Shift+Enter for newline
        def _(event):
            # Just add a plain newline
            event.app.current_buffer.insert_text('\n')
            
        @bindings.add('c-c')  # Ctrl+C
        def _(event):
            # Exit cleanly without greying out
            event.app.exit(exception=KeyboardInterrupt)
            
        try:
            # Get input with prompt_toolkit
            user_input = prompt(
                HTML(f"<ansigreen><b>{USER_PROMPT}</b></ansigreen>"),
                multiline=True,
                key_bindings=bindings,
                prompt_continuation=lambda width, line_number, is_soft_wrap: "",
            )
            return user_input.strip()
        except KeyboardInterrupt:
            raise
        except EOFError:
            # Handle Ctrl+D
            raise KeyboardInterrupt()


def parse_arguments(registry) -> argparse.Namespace:
    """Parse command line arguments."""
    available_models = list(registry.get_available_models().keys())

    parser = argparse.ArgumentParser(description="Run an interactive LLM chat session.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default="general",
        help="Specify the initial prompt for the chat session",
    )
    parser.add_argument(
        "-m",
        "--model",
        choices=available_models,
        default=registry.get_default_model(),
        help="Specify which model to use",
    )
    parser.add_argument(
        "-r",
        "--resume",
        nargs="?",
        const="",
        metavar="CHAT_ID",
        help="Resume a chat: no ID shows selector, with ID loads specific chat",
    )
    parser.add_argument(
        "-c",
        "--continue",
        action="store_true",
        help="Continue the most recent chat",
    )
    parser.add_argument(
        "--search",
        action="store_true",
        help="Enable search (if supported by model)",
    )
    parser.add_argument(
        "--thinking",
        action="store_true",
        default=True,
        help="Enable thinking mode (if supported by model)",
    )
    parser.add_argument(
        "--hide-thinking",
        action="store_true",
        help="Hide thinking trace display",
    )

    return parser.parse_args()


def setup_configuration(
    args: argparse.Namespace,
) -> tuple[Config, ChatManager, LLMClient, InputHandler, ChatOptions, str]:
    """Set up configuration and components.

    Args:
        args: Parsed command line arguments

    Returns:
        Tuple of (config, chat_manager, llm_client, input_handler, chat_options, prompt_str)
    """
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


def handle_chat_selection(
    args: argparse.Namespace, chat_manager: ChatManager
) -> Optional[Chat]:
    """Handle chat selection/loading based on arguments.

    Args:
        args: Parsed command line arguments
        chat_manager: Chat manager instance

    Returns:
        Chat instance if found/selected, None if new chat should be created
    """
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
    args: argparse.Namespace,
    chat_manager: ChatManager,
    input_handler: InputHandler,
    llm_client: LLMClient,
    prompt_str: str,
    chat_options: ChatOptions,
) -> Optional[Chat]:
    """Create a new chat session.

    Args:
        args: Parsed command line arguments
        chat_manager: Chat manager instance
        input_handler: Input handler for user input
        llm_client: LLM client for API calls
        prompt_str: System prompt string
        chat_options: Chat configuration options

    Returns:
        New chat instance, or None if user cancelled during creation
    """
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
    args: argparse.Namespace,
    chat_manager: ChatManager,
    llm_client: LLMClient,
    input_handler: InputHandler,
    chat_options: ChatOptions,
    prompt_str: str,
    is_new_chat: bool = False,
) -> None:
    """Run the main chat interaction loop.

    Args:
        current_chat: Active chat session
        args: Parsed command line arguments
        chat_manager: Chat manager instance
        llm_client: LLM client for API calls
        input_handler: Input handler for user input
        chat_options: Chat configuration options
        prompt_str: System prompt string for display
        is_new_chat: True if this is a newly created chat (skip initial display)
    """
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
