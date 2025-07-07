from importlib import resources
from typing import Dict, Tuple

import yaml

from .providers.base import LLMProvider


class ModelRegistry:
    """Registry for managing LLM providers and their models."""

    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._model_map: Dict[str, Tuple[str, str]] = (
            {}
        )  # alias -> (provider_name, model_id)
        self._default_model: str = "gpt-4o"  # fallback default
        self._load_models_and_aliases()

    def register_provider(self, name: str, provider: LLMProvider) -> None:
        """Register a provider."""
        self._providers[name] = provider

    def get_provider_for_model(self, model_alias: str) -> Tuple[LLMProvider, str]:
        """Get the provider and model ID for a given model alias."""
        if model_alias not in self._model_map:
            available_models = list(self._model_map.keys())
            raise ValueError(
                f"Unknown model: {model_alias}. Available models: {available_models}"
            )

        provider_name, model_id = self._model_map[model_alias]
        return self._providers[provider_name], model_id

    def get_available_models(self) -> Dict[str, str]:
        """Get all available model aliases."""
        return {
            alias: f"{provider_name}:{model_id}"
            for alias, (provider_name, model_id) in self._model_map.items()
        }

    def get_providers(self) -> Dict[str, LLMProvider]:
        """Get all registered providers."""
        return self._providers.copy()

    def get_default_model(self) -> str:
        """Get the default model alias."""
        return self._default_model

    def _load_models_and_aliases(self) -> None:
        """Load models and aliases from models.yaml file."""
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
                        self._model_map[model_id] = (section_name, model_id)

            # Load aliases
            aliases = config.get("aliases", {})

            # Set default model
            if "default" in aliases:
                self._default_model = aliases["default"].split("/")[
                    -1
                ]  # Extract model name

            # Load all aliases
            for alias, model_spec in aliases.items():
                if alias == "default":
                    continue

                if "/" in model_spec:
                    provider_name, model_id = model_spec.split("/", 1)
                    self._model_map[alias] = (provider_name, model_id)

        except (FileNotFoundError, yaml.YAMLError) as e:
            print(f"Warning: Could not load models from models.yaml: {e}")
            # Fallback to empty model map
