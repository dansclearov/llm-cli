import argparse
import os
import json

from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
from colored import fg, attr

from llm_cli.utils import read_system_message_from_file


load_dotenv()

# Define colors for terminal output
user_color = fg("green") + attr("bold")
gpt_color = fg("blue") + attr("bold")
system_color = fg("violet") + attr("bold")
reset_color = attr("reset")

# TODO: Move these to a config file
CHAT_DIR = "chats"
TEMP_FILE = os.path.join(CHAT_DIR, "temp_session.json")

openai = OpenAI()
anthropic = Anthropic()


def save_chat_history(messages, filename):
    filepath = os.path.join(CHAT_DIR, filename)
    with open(filepath, "w") as f:
        json.dump(messages, f, indent=2)


def load_chat_history(filename):
    filepath = os.path.join(CHAT_DIR, filename)
    with open(filepath, "r") as f:
        return json.load(f)


def save_temp_history(messages):
    with open(TEMP_FILE, "w") as f:
        json.dump(messages, f, indent=2)


def append_chat_history(filename, messages):
    filepath = os.path.join(CHAT_DIR, filename)
    with open(filepath, "r") as f:
        file_messages = json.load(f)

    # Remove the system message from the loaded history
    filtered_messages = [
        msg for msg in file_messages if msg["role"] != "system"
    ]
    messages.extend(filtered_messages)

    print_last_messages(messages)


def print_last_messages(messages, num_pairs=3):
    """
    Prints the last `num_pairs` pairs of Human and AI messages.
    """
    total_messages = len(messages)
    if total_messages <= 2 * num_pairs + 1:
        last_messages = [msg for msg in messages if msg["role"] != "system"]
    else:
        print("...")

        # Get the last `num_pairs` pairs of Human and AI messages
        last_messages = messages[-2 * num_pairs:]

    for msg in last_messages:
        role_label = "Human" if msg["role"] == "user" else "AI"
        role_color = user_color if msg["role"] == "user" else gpt_color
        print(f"{role_color}{role_label}: {reset_color}{msg['content']}")


def get_openai_response(messages, model="gpt-4o-2024-11-20"):
    completion = openai.chat.completions.create(
        model=model, messages=messages, stream=True
    )

    response_str = ""
    for chunk in completion:
        message_content = chunk.choices[0].delta.content
        if message_content:
            print(message_content, end="", flush=True)
            response_str += message_content
    return response_str


def get_anthropic_response(messages):
    with anthropic.messages.stream(
        model="claude-3-5-sonnet-latest",
        messages=messages[1:],
        system=messages[0]["content"],
        max_tokens=1024,
    ) as stream:
        response_str = ""
        for text in stream.text_stream:
            print(text, end="", flush=True)
            response_str += text
        return response_str


def get_user_input():
    """
    Allows the user to enter single-line or multi-line input
    based on a special character prefix.
    """
    first_line = input(f"{user_color}Human:{reset_color} ").strip()

    if first_line.startswith(">"):
        # Multi-line input mode
        print(
            f'{user_color}Enter multi-line input'
            f' (end with a line containing only ">>"):{reset_color}'
        )
        lines = []
        while True:
            line = input()
            if line.endswith(">>"):  # End multi-line input with '>>'
                break
            lines.append(line)
        return "\n".join(lines)
    else:
        # Single-line input mode
        return first_line


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
        help="Specify which model to use "
             "(gpt-4o, gpt-4-turbo, claude 3.5 sonnet)",
    )
    parser.add_argument(
        "--load",
        metavar="FILENAME",
        help="Load a chat history file at startup",
    )

    args = parser.parse_args()

    print(
        f"Interactive {args.model} chat session. "
        "Press Ctrl+C to exit. Use '>' to enter multi-line input."
    )

    prompt_str = read_system_message_from_file(
        "prompt_" + args.prompt + ".txt"
    )
    if args.load:
        messages = load_chat_history(args.load)

        # Show system message if it differs
        loaded_system_message = next(
            (msg["content"] for msg in messages if msg["role"] == "system"), ""
        )
        if loaded_system_message != prompt_str:
            print(f"{system_color}System (loaded):{reset_color} {loaded_system_message}")
        else:
            print(f"{system_color}System:{reset_color} {prompt_str}")

        # Print last three pairs of messages
        print_last_messages(messages)
    else:
        # Start with a fresh session
        messages = [{"role": "system", "content": prompt_str}]
        print(f"{system_color}System:{reset_color} {prompt_str}")

    finished = True
    while True:
        try:
            user_input = get_user_input()

            # Check for special commands
            if user_input.startswith("%save"):
                _, filename = user_input.split(maxsplit=1)
                save_chat_history(messages, filename)
                continue
            elif user_input.startswith("%load"):
                _, filename = user_input.split(maxsplit=1)
                messages = load_chat_history(filename)
                print_last_messages(messages)
                continue
            elif user_input.startswith("%append"):
                _, filename = user_input.split(maxsplit=1)
                append_chat_history(filename, messages)
                continue

            messages.append({"role": "user", "content": user_input})

            finished = False
            print(f"{gpt_color}AI:{reset_color}", end=" ", flush=True)

            if args.model == "gpt-4o":
                response = get_openai_response(messages)
            elif args.model == "gpt-4-turbo":
                response = get_openai_response(messages, model="gpt-4-turbo")
            else:
                response = get_anthropic_response(messages)

            messages.append({"role": "assistant", "content": response})

            print()
            finished = True

        except KeyboardInterrupt:
            if not finished:
                finished = True
                print("", flush=True)
            else:
                save_temp_history(messages)
                break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
