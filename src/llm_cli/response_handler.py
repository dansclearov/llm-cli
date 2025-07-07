from .providers.base import ChatOptions, ModelCapabilities, StreamChunk
from .renderers import StyledRenderer, PlainTextRenderer, ResponseRenderer


class ResponseHandler:
    """Handles streaming responses from different providers uniformly."""

    def __init__(
        self,
        capabilities: ModelCapabilities,
        options: ChatOptions,
        use_styled_output: bool = False,
    ):
        self.capabilities = capabilities
        self.options = options

        # Choose renderer based on flag
        if use_styled_output:
            self.renderer: ResponseRenderer = StyledRenderer(capabilities, options)
        else:
            self.renderer: ResponseRenderer = PlainTextRenderer(capabilities, options)

    def start_response(self) -> None:
        """Initialize the response rendering."""
        self.renderer.start_response()

    def handle_chunk(self, chunk: StreamChunk) -> str:
        """Handle a single streaming chunk and return any content added."""
        return self.renderer.handle_chunk(chunk)

    def finish_response(self) -> None:
        """Finalize the response rendering."""
        self.renderer.finish_response()

    def get_full_response(self) -> str:
        """Get the complete response content."""
        return self.renderer.get_full_response()

    def mark_interrupted(self) -> None:
        """Mark the response as interrupted by user."""
        self.renderer.mark_interrupted()
