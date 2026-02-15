import yaml
from unittest.mock import patch, mock_open
import pytest
from importlib import resources

from llm_cli.config.loaders import load_models_and_aliases
from llm_cli.exceptions import ConfigurationError


class TestLoadModelsAndAliases:
    def test_load_package_config_only(self):
        package_config = {
            "openai": {
                "gpt-4o": {
                    "max_tokens": 4096,
                    "supports_search": False,
                    "supports_thinking": False,
                }
            },
            "aliases": {"default": "openai/gpt-4o", "fast": "openai/gpt-4o"},
        }

        with patch("llm_cli.config.loaders.resources.files") as mock_files:
            with patch("llm_cli.config.loaders.Path.exists", return_value=False):
                mock_files.return_value.joinpath.return_value.open.return_value.__enter__.return_value = yaml.dump(
                    package_config
                )

                model_map, default_model = load_models_and_aliases()

                # Should load models from openai section
                assert "gpt-4o" in model_map
                assert model_map["gpt-4o"] == ("openai", "gpt-4o")

                # Should load aliases
                assert "fast" in model_map
                assert model_map["fast"] == ("openai", "gpt-4o")

                # Should set default model
                assert default_model == "gpt-4o"

    def test_load_with_user_override(self):
        package_config = {
            "openai": {"gpt-4o": {"max_tokens": 4096}},
            "aliases": {"default": "openai/gpt-4o", "fast": "openai/gpt-4o"},
        }

        user_config = {
            "anthropic": {"claude-3-5-sonnet": {"max_tokens": 8192}},
            "aliases": {
                "default": "anthropic/claude-3-5-sonnet",
                "smart": "anthropic/claude-3-5-sonnet",
            },
        }

        with patch("llm_cli.config.loaders.resources.files") as mock_files:
            with patch("llm_cli.config.loaders.Path.exists", return_value=True):
                with patch(
                    "builtins.open", mock_open(read_data=yaml.dump(user_config))
                ):
                    mock_files.return_value.joinpath.return_value.open.return_value.__enter__.return_value = yaml.dump(
                        package_config
                    )

                    model_map, default_model = load_models_and_aliases()

                    # Should have models from both configs
                    assert "gpt-4o" in model_map
                    assert "claude-3-5-sonnet" in model_map

                    # User aliases should be merged with package aliases
                    assert "smart" in model_map  # User alias added
                    assert "fast" in model_map  # Package alias preserved
                    assert model_map["fast"] == (
                        "openai",
                        "gpt-4o",
                    )  # Still points to package model

                    # Default should be from user config
                    assert default_model == "claude-3-5-sonnet"

    def test_invalid_yaml_package(self):
        with patch("llm_cli.config.loaders.resources.files") as mock_files:
            mock_files.return_value.joinpath.return_value.open.return_value.__enter__.return_value.read.return_value = "invalid: yaml: content: ["

            with pytest.raises(ConfigurationError) as exc_info:
                load_models_and_aliases()

            assert "Invalid YAML in models.yaml" in str(exc_info.value)

    def test_invalid_yaml_user(self):
        package_config = {
            "openai": {"gpt-4o": {}},
            "aliases": {"default": "openai/gpt-4o"},
        }

        with patch("llm_cli.config.loaders.resources.files") as mock_files:
            with patch("llm_cli.config.loaders.Path.exists", return_value=True):
                with patch("builtins.open", mock_open(read_data="invalid: yaml: [")):
                    mock_files.return_value.joinpath.return_value.open.return_value.__enter__.return_value = yaml.dump(
                        package_config
                    )

                    with pytest.raises(ConfigurationError) as exc_info:
                        load_models_and_aliases()

                    assert "Invalid YAML in user models.yaml" in str(exc_info.value)

    def test_missing_package_config(self):
        with patch("llm_cli.config.loaders.resources.files") as mock_files:
            mock_files.return_value.joinpath.return_value.open.side_effect = (
                FileNotFoundError()
            )

            with pytest.raises(ConfigurationError) as exc_info:
                load_models_and_aliases()

            assert "models.yaml not found" in str(exc_info.value)

    def test_alias_parsing(self):
        config = {
            "openai": {"gpt-4o": {}},
            "anthropic": {"claude-3-5-sonnet": {}},
            "aliases": {
                "default": "openai/gpt-4o",
                "sonnet": "anthropic/claude-3-5-sonnet",
                "invalid-alias": "no-slash-format",  # Should be ignored
            },
        }

        with patch("llm_cli.config.loaders.resources.files") as mock_files:
            with patch("llm_cli.config.loaders.Path.exists", return_value=False):
                mock_files.return_value.joinpath.return_value.open.return_value.__enter__.return_value = yaml.dump(
                    config
                )

                model_map, default_model = load_models_and_aliases()

                # Valid aliases should be loaded
                assert "sonnet" in model_map
                assert model_map["sonnet"] == ("anthropic", "claude-3-5-sonnet")

                # Invalid alias should be ignored
                assert "invalid-alias" not in model_map

    def test_merge_provider_sections(self):
        package_config = {
            "openai": {"gpt-4o": {"max_tokens": 4096}},
            "aliases": {"default": "openai/gpt-4o"},
        }

        user_config = {
            "openai": {"gpt-3.5-turbo": {"max_tokens": 2048}},  # Extends openai section
            "anthropic": {"claude-3": {"max_tokens": 8192}},  # New section
        }

        with patch("llm_cli.config.loaders.resources.files") as mock_files:
            with patch("llm_cli.config.loaders.Path.exists", return_value=True):
                with patch(
                    "builtins.open", mock_open(read_data=yaml.dump(user_config))
                ):
                    mock_files.return_value.joinpath.return_value.open.return_value.__enter__.return_value = yaml.dump(
                        package_config
                    )

                    model_map, default_model = load_models_and_aliases()

                    # Should have models from both package and user configs
                    assert "gpt-4o" in model_map
                    assert "gpt-3.5-turbo" in model_map
                    assert "claude-3" in model_map

    def test_package_alias_targets_exist(self):
        with resources.files("llm_cli").joinpath("models.yaml").open("r") as f:
            config = yaml.safe_load(f) or {}

        providers = {
            key: value
            for key, value in config.items()
            if key != "aliases" and not key.startswith("_") and isinstance(value, dict)
        }
        aliases = config.get("aliases", {})

        for alias_name, model_spec in aliases.items():
            if alias_name == "default":
                continue
            if "/" not in model_spec:
                continue

            provider_name, model_id = model_spec.split("/", 1)
            assert provider_name in providers
            assert model_id in providers[provider_name]
