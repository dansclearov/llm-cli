import os
from typing import Dict, Generator, List

from openai import OpenAI

from ..utils import get_model_capabilities
from .base import ChatOptions, LLMProvider, ModelCapabilities, StreamChunk


class DeepSeekProvider(LLMProvider):
    """Provider for DeepSeek models."""

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
        )

    def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get capabilities for DeepSeek models."""
        config = get_model_capabilities("deepseek", model)

        return ModelCapabilities(
            supports_search=config["supports_search"],
            supports_thinking=config["supports_thinking"],
            max_tokens=config["max_tokens"],
        )

    def stream_response(
        self, messages: List[Dict[str, str]], model: str, options: ChatOptions
    ) -> Generator[StreamChunk, None, None]:
        """Stream response from DeepSeek API."""
        try:
            # DeepSeek R1 supports reasoning traces
            completion = self.client.chat.completions.create(
                model=model, messages=messages, stream=True
            )

            for chunk in completion:
                delta = chunk.choices[0].delta

                # Handle reasoning content (R1 specific)
                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    yield StreamChunk(thinking=delta.reasoning_content)

                # Handle regular content
                if delta.content:
                    yield StreamChunk(content=delta.content)

        except Exception as e:
            # Let the error propagate - main.py will handle retries
            raise e
