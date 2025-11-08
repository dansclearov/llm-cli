from typing import Dict, Tuple

from llm_cli.config.loaders import load_models_and_aliases
from llm_cli.exceptions import ModelNotFoundError
from llm_cli.providers.base import LLMProvider

# Aliases to exclude from display models
EXCLUDED_ALIASES = {"default"}


class ModelRegistry:
    """Registry for managing LLM providers and their models."""

    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._model_map: Dict[str, Tuple[str, str]] = {}
        self._aliases: Dict[str, Tuple[str, str]] = {}
        self._default_model: str = "gpt-4o"  # fallback default
        self._load_models_and_aliases()

    def register_provider(self, name: str, provider: LLMProvider) -> None:
        """Register a provider."""
        self._providers[name] = provider

    def get_provider_for_model(self, model_alias: str) -> Tuple[LLMProvider, str]:
        """Get the provider and model ID for a given model alias."""
        if model_alias not in self._model_map:
            available_models = list(self._model_map.keys())
            raise ModelNotFoundError(
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

    def get_model_capabilities(self, model_alias: str):
        """Get capabilities for a specific model."""
        provider, model_id = self.get_provider_for_model(model_alias)
        return provider.get_capabilities(model_id)

    def get_display_models(self) -> list[str]:
        """Get models for CLI display, preferring aliases over full names."""
        alias_targets = {
            alias: target
            for alias, target in self._aliases.items()
            if alias not in EXCLUDED_ALIASES
        }

        display_models = set(alias_targets.keys())

        alias_target_values = set(alias_targets.values())
        for model_alias, mapping in self._model_map.items():
            if model_alias == mapping[1] and mapping not in alias_target_values:
                display_models.add(model_alias)

        return sorted(display_models)

    def _load_models_and_aliases(self) -> None:
        """Load models and aliases from models.yaml file."""
        self._model_map, self._default_model = load_models_and_aliases()
        self._aliases = {
            alias: mapping
            for alias, mapping in self._model_map.items()
            if alias != mapping[1]
        }
