"""Configuration loaders for model registry."""

import copy
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Tuple

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


def _deep_merge_models_section(
    package_section: Dict[str, Any], user_section: Dict[str, Any]
) -> Dict[str, Any]:
    """Deep-merge model configs inside one provider section."""
    merged_section = copy.deepcopy(package_section)

    for model_id, model_config in user_section.items():
        package_model_config = merged_section.get(model_id)
        if isinstance(package_model_config, dict) and isinstance(model_config, dict):
            package_model_config.update(model_config)
        else:
            merged_section[model_id] = copy.deepcopy(model_config)

    return merged_section


def _merge_model_configs(
    package_config: Dict[str, Any], user_config: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge package + user model configs with alias override semantics."""
    merged_config = copy.deepcopy(package_config)

    for section_name, section_data in user_config.items():
        if section_name.startswith("_"):
            continue

        if section_name == "aliases":
            if isinstance(section_data, dict):
                package_aliases = merged_config.get("aliases")
                if not isinstance(package_aliases, dict):
                    package_aliases = {}
                package_aliases.update(section_data)
                merged_config["aliases"] = package_aliases
            continue

        if not isinstance(section_data, dict):
            merged_config[section_name] = copy.deepcopy(section_data)
            continue

        package_section = merged_config.get(section_name)
        if isinstance(package_section, dict):
            merged_config[section_name] = _deep_merge_models_section(
                package_section, section_data
            )
        else:
            merged_config[section_name] = copy.deepcopy(section_data)

    return merged_config


def load_merged_model_config() -> Dict[str, Any]:
    """Load and merge package + user models.yaml configuration."""
    try:
        with resources.files("llm_cli").joinpath("models.yaml").open("r") as f:
            package_config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise ConfigurationError("models.yaml not found")
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in models.yaml: {e}")
    except Exception as e:
        raise ConfigurationError(f"Error loading models from models.yaml: {e}")

    if not isinstance(package_config, dict):
        raise ConfigurationError("Invalid models.yaml: top-level mapping required")

    user_config_path = _ensure_user_config()
    user_config: Dict[str, Any] = {}
    if user_config_path.exists():
        try:
            with open(user_config_path, "r") as f:
                loaded_user_config = yaml.safe_load(f) or {}
                if not isinstance(loaded_user_config, dict):
                    raise ConfigurationError(
                        "Invalid user models.yaml: top-level mapping required"
                    )
                user_config = loaded_user_config
        except ConfigurationError:
            raise
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in user models.yaml: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading user models.yaml: {e}")

    return _merge_model_configs(package_config, user_config)


def load_models_and_aliases() -> Tuple[Dict[str, Tuple[str, str]], str]:
    """Load model map and default alias from merged models.yaml config.

    Loads package models.yaml first, then merges with user models.yaml if it exists.
    User config takes precedence for aliases and default model.

    Returns:
        Tuple of (model_map, default_model)
    """
    model_map = {}
    default_model = DEFAULT_FALLBACK_MODEL  # fallback default

    merged_config = load_merged_model_config()

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
    default_spec = aliases.get("default")
    if isinstance(default_spec, str):
        if "/" in default_spec:
            _, default_model = default_spec.split("/", 1)
        else:
            default_model = default_spec

    # Load all aliases
    for alias, model_spec in aliases.items():
        if alias == "default":
            continue

        if "/" in model_spec:
            provider_name, model_id = model_spec.split("/", 1)
            model_map[alias] = (provider_name, model_id)

    return model_map, default_model
