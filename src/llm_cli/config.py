"""Configuration for LLM CLI."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_data_dir

from .providers.anthropic_provider import AnthropicProvider
from .providers.deepseek_provider import DeepSeekProvider
from .providers.gemini_provider import GeminiProvider
from .providers.openai_provider import OpenAIProvider
from .providers.xai_provider import XAIProvider
from .registry import ModelRegistry


@dataclass
class Config:
    chat_dir: str = field(
        default_factory=lambda: os.getenv(
            "LLM_CLI_CHAT_DIR",
            str(Path(user_data_dir("llm_cli", ensure_exists=True)) / "chats"),
        )
    )
    temp_file: str = field(
        default_factory=lambda: os.getenv("LLM_CLI_TEMP_FILE", "temp_session.json")
    )
    max_history_pairs: int = 3


def setup_providers() -> ModelRegistry:
    """Set up and register all LLM providers."""
    registry = ModelRegistry()

    # Register all providers
    registry.register_provider("openai", OpenAIProvider())
    registry.register_provider("anthropic", AnthropicProvider())
    registry.register_provider("deepseek", DeepSeekProvider())
    registry.register_provider("xai", XAIProvider())
    registry.register_provider("gemini", GeminiProvider())

    return registry
