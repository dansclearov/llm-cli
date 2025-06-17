import re
from importlib import resources
from pathlib import Path
from typing import Any, Dict

import yaml
from platformdirs import user_config_dir


def read_system_message_from_file(file_name: str) -> str:
    """Read system message from a prompt file, checking user config first then package."""
    # First try user config directory
    config_dir = Path(user_config_dir("llm_cli", ensure_exists=True)) / "prompts"
    config_dir.mkdir(exist_ok=True)
    user_prompt = config_dir / file_name

    if user_prompt.exists():
        with open(user_prompt, "r") as file:
            return file.read()

    # Fall back to package prompts
    try:
        with resources.files("llm_cli.prompts").joinpath(file_name).open("r") as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Prompt file {file_name} not found in either "
            f"{config_dir} or package prompts"
        )


def get_prompts() -> list[str]:
    """Get available prompts from both user config and package directories."""
    prompts = set()  # Use set to avoid duplicates
    pattern = r"prompt_(.+)\.txt"

    # Check user config directory
    config_dir = Path(user_config_dir("llm_cli", ensure_exists=True)) / "prompts"
    config_dir.mkdir(exist_ok=True)

    # Add prompts from user config
    for file in config_dir.glob("prompt_*.txt"):
        if match := re.match(pattern, file.name):
            prompts.add(match.group(1))

    # Add prompts from package
    try:
        for file in resources.files("llm_cli.prompts").iterdir():
            if match := re.match(pattern, file.name):
                prompts.add(match.group(1))
    except (TypeError, ModuleNotFoundError):
        pass  # Handle case where package prompts directory doesn't exist

    return sorted(list(prompts))  # Return sorted list for consistent ordering


def load_model_capabilities() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Load model capabilities from YAML config, merging user config with package config."""
    # Start with package config as base
    base_config = {}
    try:
        with resources.files("llm_cli").joinpath("models.yaml").open("r") as file:
            base_config = yaml.safe_load(file) or {}
    except FileNotFoundError:
        pass

    # Load user config and merge on top
    config_dir = Path(user_config_dir("llm_cli", ensure_exists=True))
    user_config = config_dir / "models.yaml"

    if user_config.exists():
        try:
            with open(user_config, "r") as file:
                user_config_data = yaml.safe_load(file) or {}
                # Deep merge user config into base config
                for provider, models in user_config_data.items():
                    if provider not in base_config:
                        base_config[provider] = {}
                    base_config[provider].update(models)
        except Exception:
            pass  # If user config is malformed, just use base config

    return base_config


def get_model_capabilities(provider_name: str, model_id: str) -> Dict[str, Any]:
    """Get capabilities for a specific model with defaults."""
    config = load_model_capabilities()

    # Get model config or empty dict
    model_config = config.get(provider_name, {}).get(model_id, {})

    # Apply defaults
    return {
        "supports_search": model_config.get("supports_search", False),
        "supports_thinking": model_config.get("supports_thinking", False),
        "max_tokens": model_config.get("max_tokens", None),
    }
