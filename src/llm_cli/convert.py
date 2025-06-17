import argparse
import json
import os
import pathlib
import sys
from dataclasses import dataclass
from typing import Dict, List

from platformdirs import user_config_dir, user_data_dir


@dataclass
class ConversionConfig:
    """Configuration settings for the conversion process."""

    chat_dir: pathlib.Path = (
        pathlib.Path(user_data_dir("llm_cli", ensure_exists=True)) / "chats"
    )
    vim_colors: Dict[str, str] = None

    def __post_init__(self):
        if self.vim_colors is None:
            self.vim_colors = {
                "system": "magenta",  # closest to purple
                "human": "green",
                "ai": "blue",
            }


class ChatConverter:
    """Handles the conversion of chat logs from JSON to Markdown format."""

    def __init__(self, config: ConversionConfig):
        self.config = config

    def generate_vim_syntax(self) -> str:
        """Generate Vim syntax highlighting rules."""
        syntax_rules = []

        # Add syntax matching rules
        syntax_rules.extend(
            [
                "syntax match System /^System:/",
                "syntax match Human /^Human:/",
                "syntax match AI /^AI:/",
            ]
        )

        # Add highlighting rules
        syntax_rules.extend(
            [
                f'hi System ctermfg={self.config.vim_colors["system"]} guifg={self.config.vim_colors["system"]}',
                f'hi Human ctermfg={self.config.vim_colors["human"]} guifg={self.config.vim_colors["human"]}',
                f'hi AI ctermfg={self.config.vim_colors["ai"]} guifg={self.config.vim_colors["ai"]}',
            ]
        )

        return "\n".join(syntax_rules)

    def write_vim_syntax_file(self) -> pathlib.Path:
        """Write Vim syntax rules to temporary file and return its path."""
        syntax_content = self.generate_vim_syntax()
        temp_path = pathlib.Path("/tmp/chat_syntax.vim")
        try:
            temp_path.write_text(syntax_content)
            return temp_path
        except OSError as e:
            print(f"Error writing syntax file: {e}", file=sys.stderr)
            sys.exit(1)

    def list_chats(self) -> List[str]:
        """List all available chat files in the chat directory."""
        try:
            self.config.chat_dir.mkdir(parents=True, exist_ok=True)
            chat_files = sorted(f.name for f in self.config.chat_dir.glob("*.json"))
            return chat_files
        except OSError as e:
            print(f"Error accessing chat directory: {e}", file=sys.stderr)
            sys.exit(1)

    def convert_chat(self, json_path: pathlib.Path, md_path: pathlib.Path) -> None:
        """
        Convert chat from JSON to Markdown format.

        Args:
            json_path: Path to input JSON file
            md_path: Path to output Markdown file
        """
        try:
            chat = json.loads(json_path.read_text())
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file: {e}", file=sys.stderr)
            sys.exit(1)
        except OSError as e:
            print(f"Error reading input file: {e}", file=sys.stderr)
            sys.exit(1)

        try:
            with md_path.open("w") as f:
                for msg in chat:
                    role = msg["role"]
                    content = msg["content"]

                    # Map roles to prefixes
                    prefix = {
                        "system": "System",
                        "user": "Human",
                        "assistant": "AI",
                    }.get(role, role.capitalize())

                    f.write(f"{prefix}: {content}\n")
        except OSError as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse and validate command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert chat JSON logs to Markdown format"
    )
    parser.add_argument(
        "json_file", type=str, nargs="?", help="Input JSON file (filename or path)"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        help="Output Markdown file (defaults to input filename with .md extension)",
    )
    parser.add_argument(
        "-v", "--view", action="store_true", help="Open in nvim after converting"
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="List all available chat files"
    )
    return parser.parse_args()


def main() -> None:
    """Main entry point for the script."""
    args = parse_args()

    config = ConversionConfig()
    converter = ChatConverter(config)

    if args.list:
        chat_files = converter.list_chats()
        if chat_files:
            print("Available chat files:")
            for file in chat_files:
                print(f"  {file}")
        else:
            print("No chat files found.")
        return

    # Check if json_file is provided when not listing
    if not args.json_file:
        parser = argparse.ArgumentParser(
            description="Convert chat JSON logs to Markdown format"
        )
        parser.error("json_file is required when not using --list")

    # Handle file paths
    json_path = (
        config.chat_dir / args.json_file
        if not pathlib.Path(args.json_file).is_absolute()
        else pathlib.Path(args.json_file)
    )

    if not json_path.suffix:
        json_path = json_path.with_suffix(".json")

    # Set output path if not specified
    if args.output:
        output_path = args.output
    else:
        output_name = pathlib.Path(args.json_file).stem + ".md"
        output_path = pathlib.Path(output_name)

    # Perform conversion
    syntax_file = converter.write_vim_syntax_file() if args.view else None
    converter.convert_chat(json_path, output_path)

    # Open in nvim if requested
    if args.view:
        try:
            os.system(f'nvim -c "source {syntax_file}" {output_path}')
        finally:
            # Clean up temporary files
            syntax_file.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
