import json
import os
from typing import Dict, Generator, List

import requests

from llm_cli.model_config import get_model_capabilities
from .base import ChatOptions, LLMProvider, ModelCapabilities, StreamChunk


class GeminiProvider(LLMProvider):
    """Provider for Google Gemini models."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def get_capabilities(self, model: str) -> ModelCapabilities:
        """Get capabilities for Gemini models."""
        config = get_model_capabilities("gemini", model)

        return ModelCapabilities(
            supports_search=config["supports_search"],
            supports_thinking=config["supports_thinking"],
            max_tokens=config["max_tokens"],
        )

    def stream_response(
        self, messages: List[Dict[str, str]], model: str, options: ChatOptions
    ) -> Generator[StreamChunk, None, None]:
        """Stream response from Gemini API."""
        try:
            # Convert OpenAI format to Gemini format
            payload = {"contents": []}

            # Handle system message
            system_msg = next(
                (msg["content"] for msg in messages if msg["role"] == "system"), None
            )
            if system_msg:
                payload["system_instruction"] = {"parts": [{"text": system_msg}]}

            # Convert conversation messages
            for msg in messages:
                if msg["role"] == "system":
                    continue
                role = "model" if msg["role"] == "assistant" else "user"
                payload["contents"].append(
                    {"role": role, "parts": [{"text": msg["content"]}]}
                )

            # Make streaming request
            response = requests.post(
                f"{self.base_url}/{model}:streamGenerateContent?alt=sse",
                headers={"Content-Type": "application/json"},
                json=payload,
                params={"key": self.api_key},
                stream=True,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line.startswith(b"data: "):
                    try:
                        data = json.loads(line[6:].decode("utf-8"))
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        yield StreamChunk(content=text)
                    except (KeyError, json.JSONDecodeError):
                        continue

        except Exception as e:
            # Let the error propagate - main.py will handle retries
            raise e
