"""Configuration for LLM CLI."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_data_dir

from llm_cli.config.user_config import load_user_config
from llm_cli.providers.anthropic_provider import AnthropicProvider
from llm_cli.providers.deepseek_provider import DeepSeekProvider
from llm_cli.providers.gemini_provider import GeminiProvider
from llm_cli.providers.openai_provider import OpenAIProvider
from llm_cli.providers.openrouter_provider import OpenRouterProvider
from llm_cli.providers.xai_provider import XAIProvider
from llm_cli.registry import ModelRegistry


@dataclass
class Config:
    chat_dir: str = field(
        default_factory=lambda: os.getenv(
            "LLM_CLI_CHAT_DIR",
            str(Path(user_data_dir("llm_cli", ensure_exists=True)) / "chats"),
        )
    )
    vim_mode: bool = field(
        default_factory=lambda: load_user_config().get("vim_mode", False)
    )


def setup_providers() -> ModelRegistry:
    """Set up and register all LLM providers."""
    registry = ModelRegistry()

    # Register all providers
    registry.register_provider("openai", OpenAIProvider())
    registry.register_provider("anthropic", AnthropicProvider())
    registry.register_provider("deepseek", DeepSeekProvider())
    registry.register_provider("xai", XAIProvider())
    registry.register_provider("gemini", GeminiProvider())
    registry.register_provider("openrouter", OpenRouterProvider())

    return registry
