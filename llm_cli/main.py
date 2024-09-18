import argparse

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


openai = OpenAI()
anthropic = Anthropic()


def get_openai_response(messages, model="gpt-4o"):
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
        model="claude-3-5-sonnet-20240620",
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
        help="Specify which model to use (gpt-4o, gpt-4-turbo, claude opus)",
    )

    args = parser.parse_args()

    print(
        f"Interactive {args.model} chat session."
        "Press Ctrl+C to exit. Use '>' to enter multi-line input."
    )

    prompt_str = read_system_message_from_file(
        "prompt_" + args.prompt + ".txt"
    )
    print(f"{system_color}System:{reset_color} {prompt_str}")

    messages = [{"role": "system", "content": prompt_str}]

    finished = True
    while True:
        try:
            user_input = get_user_input()
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
                break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
