from llm_cli.config.settings import Config, setup_providers
from llm_cli.core.client import LLMClient


# Test Config
def test_config_defaults():
    config = Config()
    assert isinstance(config.chat_dir, str)


# Test LLMClient
def test_llm_client_init():
    registry = setup_providers()
    client = LLMClient(registry)
    assert client.registry is not None
    assert client.registry == registry
