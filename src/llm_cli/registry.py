from typing import Dict, Tuple

from .providers.base import LLMProvider


class ModelRegistry:
    """Registry for managing LLM providers and their models."""

    def __init__(self):
        self._providers: Dict[str, LLMProvider] = {}
        self._model_map: Dict[str, Tuple[str, str]] = (
            {}
        )  # alias -> (provider_name, model_id)

    def register_provider(self, name: str, provider: LLMProvider) -> None:
        """Register a provider and its models."""
        self._providers[name] = provider

        # Auto-register models from provider
        for alias, model_id in provider.get_available_models().items():
            self._model_map[alias] = (name, model_id)

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
