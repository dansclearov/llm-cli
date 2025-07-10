import argparse
from llm_cli.registry import ModelRegistry


def parse_arguments(registry: ModelRegistry) -> argparse.Namespace:
    """Parse command line arguments."""
    available_models = registry.get_display_models()

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
    parser.add_argument(
        "--user-paths",
        action="store_true",
        help="Print all user path locations and exit",
    )

    return parser.parse_args()