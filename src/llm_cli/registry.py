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
        self._model_map: Dict[
            str, Tuple[str, str]
        ] = {}  # alias -> (provider_name, model_id)
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

    def get_display_models(self) -> list[str]:
        """Get models for CLI display, preferring aliases over full names."""
        # Use the merged config that includes user-defined aliases
        _, _ = load_models_and_aliases()
        from importlib import resources
        from pathlib import Path
        import yaml
        from platformdirs import user_config_dir

        # Load package models.yaml
        with resources.files("llm_cli").joinpath("models.yaml").open("r") as f:
            config = yaml.safe_load(f)

        # Load user models.yaml if it exists and merge
        user_config_path = Path(user_config_dir("llm_cli")) / "models.yaml"
        if user_config_path.exists():
            with open(user_config_path, "r") as f:
                user_config = yaml.safe_load(f) or {}
                if "aliases" in user_config:
                    config["aliases"] = user_config["aliases"]

        aliases = set(config.get("aliases", {}).keys()) - EXCLUDED_ALIASES
        all_models = set(self._model_map.keys())

        # Show aliases + models that don't have aliases
        display_models = []
        for model in all_models:
            if model in aliases:
                display_models.append(model)
            else:
                # Check if any alias points to this model
                has_alias = False
                for alias in aliases:
                    if (
                        alias in self._model_map
                        and self._model_map[alias] == self._model_map[model]
                    ):
                        has_alias = True
                        break
                if not has_alias:
                    display_models.append(model)

        return sorted(display_models)

    def _load_models_and_aliases(self) -> None:
        """Load models and aliases from models.yaml file."""
        self._model_map, self._default_model = load_models_and_aliases()
