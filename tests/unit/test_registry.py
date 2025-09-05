import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch
import pytest

from llm_cli.registry import ModelRegistry
from llm_cli.exceptions import ModelNotFoundError
from llm_cli.providers.base import LLMProvider


class MockProvider(LLMProvider):
    def get_capabilities(self, model):
        return {"max_tokens": 1000, "supports_search": False, "supports_thinking": False}
    
    def stream_response(self, messages, model, options):
        yield {"content": "test response"}


class TestModelRegistry:
    def test_register_provider(self):
        registry = ModelRegistry()
        provider = MockProvider()
        registry.register_provider("test", provider)
        
        assert "test" in registry.get_providers()
        assert registry.get_providers()["test"] == provider

    def test_get_provider_for_model_success(self):
        with patch('llm_cli.registry.load_models_and_aliases') as mock_load:
            mock_load.return_value = ({"test-model": ("test", "test-model")}, "test-model")
            
            registry = ModelRegistry()
            provider = MockProvider()
            registry.register_provider("test", provider)
            
            result_provider, model_id = registry.get_provider_for_model("test-model")
            assert result_provider == provider
            assert model_id == "test-model"

    def test_get_provider_for_model_not_found(self):
        with patch('llm_cli.registry.load_models_and_aliases') as mock_load:
            mock_load.return_value = ({}, "default")
            
            registry = ModelRegistry()
            
            with pytest.raises(ModelNotFoundError) as exc_info:
                registry.get_provider_for_model("nonexistent")
            
            assert "Unknown model: nonexistent" in str(exc_info.value)

    def test_get_available_models(self):
        with patch('llm_cli.registry.load_models_and_aliases') as mock_load:
            mock_load.return_value = ({"model1": ("provider1", "model1"), "model2": ("provider2", "model2")}, "model1")
            
            registry = ModelRegistry()
            models = registry.get_available_models()
            
            assert models == {"model1": "provider1:model1", "model2": "provider2:model2"}

    def test_get_default_model(self):
        with patch('llm_cli.registry.load_models_and_aliases') as mock_load:
            mock_load.return_value = ({}, "test-default")
            
            registry = ModelRegistry()
            assert registry.get_default_model() == "test-default"

