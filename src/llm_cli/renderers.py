"""Output renderers for streaming LLM responses."""

from abc import ABC, abstractmethod
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Heading, Markdown
from rich.markup import escape
from rich.text import Text

from .providers.base import ChatOptions, ModelCapabilities, StreamChunk


class LeftAlignedHeading(Heading):
    """Custom heading that renders left-aligned instead of centered."""

    def __rich_console__(self, console, options):
        text = self.text
        text.justify = "left"  # Override center alignment
        yield text


class LeftAlignedMarkdown(Markdown):
    """Custom Markdown that uses left-aligned headers."""

    elements = {
        **Markdown.elements,
        "heading_open": LeftAlignedHeading,
    }


class ResponseRenderer(ABC):
    """Abstract base class for rendering streaming LLM responses."""

    def __init__(self, capabilities: ModelCapabilities, options: ChatOptions):
        self.capabilities = capabilities
        self.options = options
        self.thinking_started = False
        self.content_started = False
        self.response_content = ""
        self.was_interrupted = False

    @abstractmethod
    def start_response(self) -> None:
        """Initialize the response rendering."""
        pass

    @abstractmethod
    def handle_chunk(self, chunk: StreamChunk) -> str:
        """Handle a single streaming chunk and return any content added."""
        pass

    @abstractmethod
    def finish_response(self) -> None:
        """Finalize the response rendering."""
        pass

    def get_full_response(self) -> str:
        """Get the complete response content."""
        return self.response_content

    def mark_interrupted(self) -> None:
        """Mark the response as interrupted by user."""
        self.was_interrupted = True


class PlainTextRenderer(ResponseRenderer):
    """Simple print-based renderer.
    
    LEGACY: Kept for rollback purposes only - do not extend.
    Use StyledRenderer instead for new features.
    """

    def start_response(self) -> None:
        """Initialize the response rendering."""
        if not self.options.silent:
            from colored import attr, fg
            from llm_cli.constants import AI_PROMPT

            AI_COLOR = fg("blue") + attr("bold")
            RESET_COLOR = attr("reset")
            print(f"{AI_COLOR}{AI_PROMPT}{RESET_COLOR}", end="", flush=True)

    def handle_chunk(self, chunk: StreamChunk) -> str:
        """Handle a single streaming chunk and return any content added."""
        content_added = ""

        # Handle thinking trace
        if chunk.thinking and self.capabilities.supports_thinking:
            if self.options.show_thinking and not self.options.silent:
                if not self.thinking_started:
                    print("<thinking>", flush=True)
                    self.thinking_started = True
                print(chunk.thinking, end="", flush=True)

        # Handle main content
        if chunk.content:
            # Close thinking section if we're transitioning to content
            if (
                self.thinking_started
                and not self.content_started
                and self.options.show_thinking
                and not self.options.silent
            ):
                print("\n</thinking>\n", flush=True)
                self.content_started = True

            if not self.options.silent:
                print(chunk.content, end="", flush=True)
            content_added = chunk.content
            self.response_content += chunk.content

        return content_added

    def finish_response(self) -> None:
        """Finalize the response rendering."""
        if not self.options.silent:
            print()  # Add newline after response


class StyledRenderer(ResponseRenderer):
    """Rich console renderer with styled thinking traces."""

    def __init__(self, capabilities: ModelCapabilities, options: ChatOptions):
        super().__init__(capabilities, options)
        self.console = Console(highlight=False)
        self.live: Optional[Live] = None
        self.thinking_content = ""
        self.last_update = 0

    def start_response(self) -> None:
        """Initialize the response rendering."""
        if not self.options.silent:
            from llm_cli.constants import AI_PROMPT
            self.console.print(Text(AI_PROMPT, style="blue bold"), end="")

    def handle_chunk(self, chunk: StreamChunk) -> str:
        """Handle a single streaming chunk and return any content added."""
        content_added = ""

        # Handle thinking trace
        if chunk.thinking and self.capabilities.supports_thinking:
            if self.options.show_thinking and not self.options.silent:
                self.console.print(
                    f"[bright_black italic]{escape(chunk.thinking)}[/bright_black italic]",
                    end="",
                )
                if not self.thinking_started:
                    self.thinking_started = True

        # Handle main content
        if chunk.content:
            # Close thinking section if we're transitioning to content
            if (
                self.thinking_started
                and not self.content_started
                and self.options.show_thinking
                and not self.options.silent
            ):
                self.console.print("\n", end="")  # Add single newline after thinking
                self.content_started = True

            if not self.options.silent:
                self.console.print(escape(chunk.content), end="")
            content_added = chunk.content
            self.response_content += chunk.content

        return content_added

    def finish_response(self) -> None:
        """Finalize the response rendering."""
        if not self.options.silent:
            self.console.print()  # Add final newline
