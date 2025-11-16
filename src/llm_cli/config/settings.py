"""Configuration for LLM CLI."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_data_dir

from llm_cli.config.user_config import load_user_config
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
    """Set up and return the model registry."""
    return ModelRegistry()
