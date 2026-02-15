from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Dict

import yaml
from platformdirs import user_config_dir

from llm_cli.exceptions import ConfigurationError


@lru_cache(maxsize=1)
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
                    if provider.startswith("_"):  # Skip anchors
                        continue
                    if provider not in base_config:
                        base_config[provider] = {}
                    if isinstance(models, dict):
                        # Merge at model level too
                        for model_id, model_config in models.items():
                            if model_id not in base_config[provider]:
                                base_config[provider][model_id] = {}
                            if isinstance(model_config, dict):
                                # Merge model properties
                                base_config[provider][model_id].update(model_config)
                            else:
                                base_config[provider][model_id] = model_config
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in user config: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading user config: {e}")

    return base_config


def clear_model_capabilities_cache() -> None:
    """Clear the in-memory capabilities cache."""
    load_model_capabilities.cache_clear()


def get_model_capabilities(provider_name: str, model_id: str) -> Dict[str, Any]:
    """Get capabilities for a specific model with defaults."""
    config = load_model_capabilities()

    # Get model config or empty dict
    model_entry = config.get(provider_name, {}).get(model_id, {})
    model_config = model_entry if isinstance(model_entry, dict) else {}
    extra_params = model_config.get("extra_params", {})
    safe_extra_params = extra_params if isinstance(extra_params, dict) else {}

    # Apply defaults
    return {
        "supports_search": model_config.get("supports_search", False),
        "supports_thinking": model_config.get("supports_thinking", False),
        "max_tokens": model_config.get("max_tokens", None),
        "extra_params": dict(safe_extra_params),
    }
