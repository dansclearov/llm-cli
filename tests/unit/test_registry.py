from unittest.mock import patch

import pytest

from llm_cli.exceptions import ModelNotFoundError
from llm_cli.registry import ModelRegistry


class TestModelRegistry:
    def test_get_provider_for_model_success(self):
        with patch("llm_cli.registry.load_models_and_aliases") as mock_load:
            mock_load.return_value = (
                {"test-model": ("test", "test-model")},
                "test-model",
            )

            registry = ModelRegistry()
            provider, model_id = registry.get_provider_for_model("test-model")

            assert provider == "test"
            assert model_id == "test-model"

    def test_get_provider_for_model_not_found(self):
        with patch("llm_cli.registry.load_models_and_aliases") as mock_load:
            mock_load.return_value = ({}, "default")

            registry = ModelRegistry()

            with pytest.raises(ModelNotFoundError) as exc_info:
                registry.get_provider_for_model("nonexistent")

            assert "Unknown model: nonexistent" in str(exc_info.value)

    def test_resolve_model_name(self):
        with patch("llm_cli.registry.load_models_and_aliases") as mock_load:
            mock_load.return_value = (
                {"alias": ("provider", "model")},
                "alias",
            )

            registry = ModelRegistry()
            assert registry.resolve_model_name("alias") == "provider:model"

    def test_get_available_models(self):
        with patch("llm_cli.registry.load_models_and_aliases") as mock_load:
            mock_load.return_value = (
                {"model1": ("provider1", "model1"), "model2": ("provider2", "model2")},
                "model1",
            )

            registry = ModelRegistry()
            models = registry.get_available_models()

            assert models == {
                "model1": "provider1:model1",
                "model2": "provider2:model2",
            }

    def test_get_default_model(self):
        with patch("llm_cli.registry.load_models_and_aliases") as mock_load:
            mock_load.return_value = ({}, "test-default")

            registry = ModelRegistry()
            assert registry.get_default_model() == "test-default"

    def test_get_model_capabilities(self):
        with (
            patch("llm_cli.registry.load_models_and_aliases") as mock_load,
            patch("llm_cli.registry.load_model_capabilities") as mock_caps,
        ):
            mock_load.return_value = (
                {"alias": ("provider", "model")},
                "alias",
            )
            mock_caps.return_value = {"supports_search": True}

            registry = ModelRegistry()
            capabilities = registry.get_model_capabilities("alias")
            assert capabilities.supports_search is True
            assert capabilities.supports_thinking is False
            mock_caps.assert_called_once_with("provider", "model")
