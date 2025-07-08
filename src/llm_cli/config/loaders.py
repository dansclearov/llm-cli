"""Configuration loaders for model registry."""

from importlib import resources
from typing import Dict, Tuple

import yaml

from llm_cli.exceptions import ConfigurationError


def load_models_and_aliases() -> Tuple[Dict[str, Tuple[str, str]], str]:
    """Load models and aliases from models.yaml file.
    
    Returns:
        Tuple of (model_map, default_model)
    """
    model_map = {}
    default_model = "gpt-4o"  # fallback default
    
    try:
        with resources.files("llm_cli").joinpath("models.yaml").open("r") as f:
            config = yaml.safe_load(f)

        # Load all models from all provider sections dynamically
        for section_name, section_data in config.items():
            if section_name == "aliases":
                continue

            # Each top-level section (except aliases) is a provider
            if isinstance(section_data, dict):
                for model_id in section_data.keys():
                    # Register model ID as direct alias
                    model_map[model_id] = (section_name, model_id)

        # Load aliases
        aliases = config.get("aliases", {})

        # Set default model
        if "default" in aliases:
            default_model = aliases["default"].split("/")[-1]  # Extract model name

        # Load all aliases
        for alias, model_spec in aliases.items():
            if alias == "default":
                continue

            if "/" in model_spec:
                provider_name, model_id = model_spec.split("/", 1)
                model_map[alias] = (provider_name, model_id)

    except FileNotFoundError:
        raise ConfigurationError("models.yaml not found")
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in models.yaml: {e}")
    except Exception as e:
        raise ConfigurationError(f"Error loading models from models.yaml: {e}")

    return model_map, default_model