import argparse
import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential
from platformdirs import user_data_dir

from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
from colored import fg, attr

from llm_cli.constants import MODEL_MAPPINGS
from llm_cli.utils import read_system_message_from_file


load_dotenv()

USER_COLOR = fg("green") + attr("bold")
AI_COLOR = fg("blue") + attr("bold")
SYSTEM_COLOR = fg("violet") + attr("bold")
RESET_COLOR = attr("reset")


@dataclass
class Config:
    chat_dir: str = field(
        default_factory=lambda: os.getenv(
            "LLM_CLI_CHAT_DIR",
            str(Path(user_data_dir("llm_cli", ensure_exists=True)) / "chats")
        )
    )
    temp_file: str = field(
        default_factory=lambda: os.getenv(
            "LLM_CLI_TEMP_FILE",
            "temp_session.json"
        )
    )
    models: Dict[str, str] = field(default_factory=lambda: MODEL_MAPPINGS)
    max_history_pairs: int = 3
    retry_attempts: int = 3
    min_retry_wait: int = 4
    max_retry_wait: int = 10


class ChatHistory:
    def __init__(self, config: Config):
        self.config = config
        self.messages: List[Dict[str, str]] = []

    def save(self, filename: str) -> None:
        """Save chat history to a file."""
        filepath = Path(self.config.chat_dir) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.messages, f, indent=2)

    def load(self, filename: str) -> None:
        """Load chat history from a file."""
        filepath = Path(self.config.chat_dir) / filename
        try:
            with open(filepath, "r") as f:
                self.messages = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Chat history file not found: {filepath}")

    def append_from_file(self, filename: str) -> None:
        """Append messages from another chat history file."""
        filepath = Path(self.config.chat_dir) / filename
        with open(filepath, "r") as f:
            file_messages = json.load(f)

        # Remove system message from loaded history
        filtered_messages = [
            msg for msg in file_messages if msg["role"] != "system"
        ]
        self.messages.extend(filtered_messages)

    def print_last_messages(self, page: int = 0) -> None:
        """Print the last N pairs of messages with optional pagination."""
        num_pairs = self.config.max_history_pairs
        total_messages = len(self.messages)

        start_idx = max(1, total_messages - (page + 1) * 2 * num_pairs)
        end_idx = total_messages - page * 2 * num_pairs

        if start_idx > 1:
            print("...")

        messages_slice = self.messages[start_idx:end_idx]
        for msg in messages_slice:
            if msg["role"] == "system":
                continue

            role_label = "Human" if msg["role"] == "user" else "AI"
            role_color = USER_COLOR if msg["role"] == "user" else AI_COLOR
            print(f"{role_color}{role_label}: {RESET_COLOR}{msg['content']}")


class LLMClient:
    def __init__(self, config: Config):
        self.config = config
        self.openai = OpenAI()
        self.anthropic = Anthropic()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_openai_response(
        self, messages: List[Dict[str, str]], model: str
    ) -> str:
        """Get response from OpenAI API with retry logic."""
        completion = self.openai.chat.completions.create(
            model=model, messages=messages, stream=True
        )

        response_str = ""
        for chunk in completion:
            message_content = chunk.choices[0].delta.content
            if message_content:
                print(message_content, end="", flush=True)
                response_str += message_content
        return response_str

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_anthropic_response(
        self, messages: List[Dict[str, str]]
    ) -> str:
        """Get response from Anthropic API with retry logic."""
        with self.anthropic.messages.stream(
            model=self.config.models["sonnet"],
            messages=messages[1:],
            system=messages[0]["content"],
            max_tokens=1024,
        ) as stream:
            response_str = ""
            for text in stream.text_stream:
                print(text, end="", flush=True)
                response_str += text
            return response_str


class InputHandler:
    @staticmethod
    def get_user_input() -> str:
        """Get single or multi-line input from user."""
        first_line = input(f"{USER_COLOR}Human:{RESET_COLOR} ").strip()

        if first_line.startswith(">"):
            print(
                f'{USER_COLOR}Enter multi-line input'
                f' (end with a line containing only ">>"):{RESET_COLOR}'
            )
            lines = []
            while True:
                line = input()
                if line.strip() == ">>":
                    break
                lines.append(line)
            return "\n".join(lines)
        return first_line

    @staticmethod
    def parse_command(input_str: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse special commands from input."""
        if not input_str.startswith("%"):
            return None, None

        parts = input_str.split(maxsplit=1)
        command = parts[0][1:]  # Remove the % prefix
        args = parts[1] if len(parts) > 1 else None

        valid_commands = {"save", "load", "append"}
        if command not in valid_commands:
            raise ValueError(f"Unknown command: {command}")

        return command, args


def main():
    parser = argparse.ArgumentParser(
        description="Run an interactive LLM chat session."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="general",
        help="Specify the initial prompt for the chat session",
    )
    parser.add_argument(
        "-m",
        "--model",
        choices=["gpt-4o", "gpt-4-turbo", "sonnet"],
        default="gpt-4o",
        help="Specify which model to use",
    )
    parser.add_argument(
        "-l",
        "--load",
        metavar="FILENAME",
        help="Load a chat history file at startup",
    )

    args = parser.parse_args()

    config = Config()
    chat_history = ChatHistory(config)
    llm_client = LLMClient(config)
    input_handler = InputHandler()

    print(
        f"Interactive {args.model} chat session. "
        "Press Ctrl+C to exit. Use '>' to enter multi-line input."
    )

    prompt_str = read_system_message_from_file(
        "prompt_" + args.prompt + ".txt"
    )

    if args.load:
        chat_history.load(args.load)

        # Show system message if it differs
        loaded_system_message = next(
            (msg["content"] for msg in chat_history.messages
                if msg["role"] == "system"),
            ""
        )
        if loaded_system_message != prompt_str:
            print(
                f"{SYSTEM_COLOR}System (loaded):{RESET_COLOR} "
                f"{loaded_system_message}"
            )
        else:
            print(f"{SYSTEM_COLOR}System:{RESET_COLOR} {prompt_str}")

        chat_history.print_last_messages()
    else:
        chat_history.messages = [{"role": "system", "content": prompt_str}]
        print(f"{SYSTEM_COLOR}System:{RESET_COLOR} {prompt_str}")

    # Main interaction loop
    finished = True
    while True:
        try:
            user_input = input_handler.get_user_input()

            # Handle special commands
            cmd, cmd_args = input_handler.parse_command(user_input)
            if cmd:
                if cmd == "save" and cmd_args:
                    chat_history.save(cmd_args)
                elif cmd == "load" and cmd_args:
                    chat_history.load(cmd_args)
                    chat_history.print_last_messages()
                elif cmd == "append" and cmd_args:
                    chat_history.append_from_file(cmd_args)
                    chat_history.print_last_messages()
                continue

            # Process normal input
            chat_history.messages.append(
                {"role": "user", "content": user_input}
            )

            finished = False
            print(f"{AI_COLOR}AI:{RESET_COLOR}", end=" ", flush=True)

            if args.model in ["gpt-4o", "gpt-4-turbo"]:
                response = llm_client.get_openai_response(
                    chat_history.messages,
                    config.models[args.model]
                )
            else:
                response = llm_client.get_anthropic_response(
                    chat_history.messages
                )

            chat_history.messages.append(
                {"role": "assistant", "content": response}
            )

            print()
            finished = True

        except KeyboardInterrupt:
            if not finished:
                finished = True
                print("", flush=True)
            else:
                chat_history.save(config.temp_file)
                break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
