from typing import Dict, Generator, List

from anthropic import Anthropic

from ..utils import get_model_capabilities
from .base import ChatOptions, LLMProvider, ModelCapabilities, StreamChunk


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic models."""

    def __init__(self):
        self.client = Anthropic()

    def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get capabilities for Anthropic models."""
        config = get_model_capabilities("anthropic", model)

        return ModelCapabilities(
            supports_search=config["supports_search"],
            supports_thinking=config["supports_thinking"],
            max_tokens=config["max_tokens"] or 4096,  # Anthropic requires max_tokens
        )

    def stream_response(
        self, messages: List[Dict[str, str]], model: str, options: ChatOptions
    ) -> Generator[StreamChunk, None, None]:
        """Stream response from Anthropic API."""
        try:
            # Anthropic expects system message separately
            system_message = (
                messages[0]["content"]
                if messages and messages[0]["role"] == "system"
                else ""
            )
            conversation_messages = messages[1:] if system_message else messages

            # Set up tools for web search if enabled and supported
            tools = []
            if options.enable_search and self.get_capabilities(model).supports_search:
                tools = [{"type": "web_search_20250305", "name": "web_search"}]

            # Get max_tokens from capabilities
            capabilities = self.get_capabilities(model)

            with self.client.messages.stream(
                model=model,
                messages=conversation_messages,
                system=system_message,
                max_tokens=capabilities.max_tokens,
                tools=tools,
            ) as stream:
                for text in stream.text_stream:
                    yield StreamChunk(content=text)

        except Exception as e:
            # Let the error propagate - main.py will handle retries
            raise e
