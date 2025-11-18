"""Configuration loaders for model registry."""

from importlib import resources
from pathlib import Path
from typing import Dict, Tuple

import yaml
from platformdirs import user_config_dir

from llm_cli.constants import DEFAULT_FALLBACK_MODEL
from llm_cli.exceptions import ConfigurationError


def _ensure_user_config() -> Path:
    """Ensure user config directory exists and create default models.yaml if missing."""
    config_dir = Path(user_config_dir("llm_cli"))
    config_dir.mkdir(parents=True, exist_ok=True)

    user_config_path = config_dir / "models.yaml"
    if not user_config_path.exists():
        # Copy template to user config
        try:
            template_content = (
                resources.files("llm_cli").joinpath("models_template.yaml").read_text()
            )
            user_config_path.write_text(template_content)
        except Exception:
            # Non-fatal: user can still use built-in models
            pass

    return user_config_path


def load_models_and_aliases() -> Tuple[Dict[str, Tuple[str, str]], str]:
    """Load models and aliases from models.yaml file.

    Loads package models.yaml first, then merges with user models.yaml if it exists.
    User config takes precedence for aliases and default model.

    Returns:
        Tuple of (model_map, default_model)
    """
    model_map = {}
    default_model = DEFAULT_FALLBACK_MODEL  # fallback default

    # Load package models.yaml
    try:
        with resources.files("llm_cli").joinpath("models.yaml").open("r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigurationError("models.yaml not found")
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in models.yaml: {e}")
    except Exception as e:
        raise ConfigurationError(f"Error loading models from models.yaml: {e}")

    # Ensure user config exists and load it
    user_config_path = _ensure_user_config()
    user_config = {}
    if user_config_path.exists():
        try:
            with open(user_config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in user models.yaml: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading user models.yaml: {e}")

    # Merge configurations (user overrides package)
    merged_config = config.copy()
    if user_config:
        # Merge provider sections (user models extend package models)
        for section_name, section_data in user_config.items():
            if section_name == "aliases":
                continue
            if isinstance(section_data, dict):
                if section_name in merged_config:
                    merged_config[section_name].update(section_data)
                else:
                    merged_config[section_name] = section_data

        # Merge aliases (user overrides specific aliases, preserves others)
        if "aliases" in user_config:
            if "aliases" not in merged_config:
                merged_config["aliases"] = {}
            merged_config["aliases"].update(user_config["aliases"])

    # Load all models from all provider sections dynamically
    for section_name, section_data in merged_config.items():
        if section_name == "aliases":
            continue

        # Skip top-level keys starting with _ (YAML anchors, metadata, etc.)
        if section_name.startswith("_"):
            continue

        # Each top-level section (except aliases) is a provider
        if isinstance(section_data, dict):
            for model_id in section_data.keys():
                # Register model ID as direct alias
                model_map[model_id] = (section_name, model_id)

    # Load aliases
    aliases = merged_config.get("aliases", {})

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

    return model_map, default_model
