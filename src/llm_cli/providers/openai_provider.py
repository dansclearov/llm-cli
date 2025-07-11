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
        """Stream response from OpenAI API."""
        try:
            completion = self.client.chat.completions.create(
                model=model, messages=messages, stream=True
            )

            for chunk in completion:
                delta = chunk.choices[0].delta

                # Handle regular content
                if delta.content:
                    yield StreamChunk(content=delta.content)

                # Note: OpenAI o1 models don't currently expose reasoning in the API
                # If they add this in the future, we'd handle it here

        except Exception as e:
            # Let the error propagate - main.py will handle retries
            raise e
