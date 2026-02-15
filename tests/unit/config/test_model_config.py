from unittest.mock import patch

import yaml

from llm_cli.model_config import (
    clear_model_capabilities_cache,
    get_model_capabilities,
    load_model_capabilities,
)


def test_load_model_capabilities_caches_yaml_reads():
    package_config = {
        "openai": {
            "gpt-4o": {
                "supports_search": True,
            }
        }
    }

    clear_model_capabilities_cache()
    try:
        with patch("llm_cli.model_config.resources.files") as mock_files:
            with patch("llm_cli.model_config.Path.exists", return_value=False):
                with patch(
                    "llm_cli.model_config.yaml.safe_load", wraps=yaml.safe_load
                ) as mock_safe_load:
                    mock_files.return_value.joinpath.return_value.open.return_value.__enter__.return_value = yaml.dump(
                        package_config
                    )

                    first = load_model_capabilities()
                    second = load_model_capabilities()

                    assert first == second
                    assert mock_safe_load.call_count == 1
    finally:
        clear_model_capabilities_cache()


def test_get_model_capabilities_copies_extra_params():
    clear_model_capabilities_cache()
    try:
        with patch(
            "llm_cli.model_config.load_model_capabilities",
            return_value={
                "provider": {
                    "model": {
                        "extra_params": {"foo": "bar"},
                        "supports_search": True,
                    }
                }
            },
        ):
            caps = get_model_capabilities("provider", "model")

            assert caps["supports_search"] is True
            assert caps["extra_params"] == {"foo": "bar"}
            caps["extra_params"]["foo"] = "changed"

            caps_again = get_model_capabilities("provider", "model")
            assert caps_again["extra_params"] == {"foo": "bar"}
    finally:
        clear_model_capabilities_cache()
