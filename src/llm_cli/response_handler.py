from .providers.base import ChatOptions, ModelCapabilities, StreamChunk


class ResponseHandler:
    """Handles streaming responses from different providers uniformly."""

    def __init__(self, capabilities: ModelCapabilities, options: ChatOptions):
        self.capabilities = capabilities
        self.options = options
        self.thinking_started = False
        self.content_started = False
        self.response_content = ""

    def handle_chunk(self, chunk: StreamChunk) -> str:
        """Handle a single streaming chunk and return any content added."""
        content_added = ""

        # Handle thinking trace
        if chunk.thinking and self.capabilities.supports_thinking:
            if self.options.show_thinking:
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
            ):
                print("\n</thinking>\n", flush=True)
                self.content_started = True

            print(chunk.content, end="", flush=True)
            content_added = chunk.content
            self.response_content += chunk.content

        return content_added

    def get_full_response(self) -> str:
        """Get the complete response content."""
        return self.response_content
