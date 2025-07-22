import json
import os
from typing import Dict, Generator, List

import requests

from llm_cli.model_config import get_model_capabilities

from .base import ChatOptions, LLMProvider, ModelCapabilities, StreamChunk


class OpenRouterProvider(LLMProvider):
    """Provider for OpenRouter models."""

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"

    def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get capabilities for OpenRouter models."""
        config = get_model_capabilities("openrouter", model)

        return ModelCapabilities(
            supports_search=config["supports_search"],
            supports_thinking=config["supports_thinking"],
            max_tokens=config["max_tokens"],
        )

    def stream_response(
        self, messages: List[Dict[str, str]], model: str, options: ChatOptions
    ) -> Generator[StreamChunk, None, None]:
        """Stream response from OpenRouter API."""
        try:
            # Get model configuration for capabilities and extra params
            config = get_model_capabilities("openrouter", model)
            capabilities = self.get_capabilities(model)
            
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
            }

            # Add reasoning parameter for models that support thinking
            if capabilities.supports_thinking:
                payload["reasoning"] = {"effort": "high", "exclude": False}
            
            # Merge any extra_params from model configuration
            extra_params = config.get("extra_params", {})
            if extra_params:
                payload.update(extra_params)

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                stream=True,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line.startswith(b"data: "):
                    chunk_data = line[6:].decode("utf-8")
                    if chunk_data == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(chunk_data)
                        if "choices" in data and data["choices"]:
                            delta = data["choices"][0].get("delta", {})
                            
                            # Handle OpenRouter reasoning content
                            if "reasoning" in delta and delta["reasoning"]:
                                yield StreamChunk(thinking=delta["reasoning"])
                            
                            # Handle regular content
                            if "content" in delta and delta["content"]:
                                yield StreamChunk(content=delta["content"])
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            # Let the error propagate - main.py will handle retries
            raise e
