from typing import Dict, Generator, List

from openai import OpenAI

from llm_cli.model_config import get_model_capabilities
from .base import ChatOptions, LLMProvider, ModelCapabilities, StreamChunk


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI models."""

    def __init__(self):
        self.client = OpenAI()

    def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get capabilities for OpenAI models."""
        config = get_model_capabilities("openai", model)

        return ModelCapabilities(
            supports_search=config["supports_search"],
            supports_thinking=config["supports_thinking"],
            max_tokens=config["max_tokens"],
        )

    def stream_response(
        self, messages: List[Dict[str, str]], model: str, options: ChatOptions
    ) -> Generator[StreamChunk, None, None]:
        """Stream response from OpenAI API using responses.create."""
        try:
            # Check capabilities
            capabilities = self.get_capabilities(model)

            # Build request parameters
            request_params = {
                "model": model,
                "input": messages,
                "stream": True,
            }

            # Add reasoning if supported and enabled
            if capabilities.supports_thinking and options.enable_thinking:
                request_params["reasoning"] = {"summary": "auto"}

            # Add web search tool if supported and enabled
            if capabilities.supports_search and options.enable_search:
                request_params["tools"] = [{"type": "web_search"}]

            response = self.client.responses.create(**request_params)

            for chunk in response:
                event_type = getattr(chunk, "type", "unknown")

                # Handle reasoning content
                if event_type == "response.reasoning_summary_text.delta":
                    if hasattr(chunk, "delta") and chunk.delta:
                        yield StreamChunk(thinking=chunk.delta)

                # Handle regular message content
                elif event_type == "response.output_text.delta":
                    if hasattr(chunk, "delta") and chunk.delta:
                        yield StreamChunk(content=chunk.delta)

                # Stop at completion
                elif event_type == "response.completed":
                    break

        except Exception as e:
            # Let the error propagate - main.py will handle retries
            raise e
