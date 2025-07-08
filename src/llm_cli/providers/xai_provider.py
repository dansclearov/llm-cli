import json
import os
from typing import Dict, Generator, List

import requests

from llm_cli.model_config import get_model_capabilities
from .base import ChatOptions, LLMProvider, ModelCapabilities, StreamChunk


class XAIProvider(LLMProvider):
    """Provider for xAI models."""

    def __init__(self):
        self.api_key = os.getenv("XAI_API_KEY")
        self.base_url = "https://api.x.ai/v1"

    def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get capabilities for xAI models."""
        config = get_model_capabilities("xai", model)

        return ModelCapabilities(
            supports_search=config["supports_search"],
            supports_thinking=config["supports_thinking"],
            max_tokens=config["max_tokens"],
        )

    def stream_response(
        self, messages: List[Dict[str, str]], model: str, options: ChatOptions
    ) -> Generator[StreamChunk, None, None]:
        """Stream response from xAI API."""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            payload = {"messages": messages, "model": model, "stream": True}

            # Add search parameters if enabled and supported
            if options.enable_search and self.get_capabilities(model).supports_search:
                payload["search_parameters"] = {"mode": "auto"}

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line.startswith(b"data: "):
                    line_data = line[6:]
                    if line_data.strip() == b"[DONE]":
                        break
                    try:
                        data = json.loads(line_data)
                        content = data["choices"][0]["delta"].get("content")
                        if content:
                            yield StreamChunk(content=content)
                    except (KeyError, json.JSONDecodeError):
                        continue

        except Exception as e:
            # Let the error propagate - main.py will handle retries
            raise e
