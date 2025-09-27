from llm_cli.providers.base import ModelCapabilities, StreamChunk, ChatOptions


class TestModelCapabilities:
    def test_default_values(self):
        caps = ModelCapabilities()

        assert not caps.supports_search
        assert not caps.supports_thinking
        assert caps.max_tokens is None

    def test_custom_values(self):
        caps = ModelCapabilities(
            supports_search=True, supports_thinking=True, max_tokens=4096
        )

        assert caps.supports_search
        assert caps.supports_thinking
        assert caps.max_tokens == 4096


class TestStreamChunk:
    def test_default_values(self):
        chunk = StreamChunk()

        assert chunk.content is None
        assert chunk.thinking is None
        assert chunk.metadata == {}

    def test_custom_values(self):
        metadata = {"token_count": 10}
        chunk = StreamChunk(
            content="Hello world",
            thinking="I should respond politely",
            metadata=metadata,
        )

        assert chunk.content == "Hello world"
        assert chunk.thinking == "I should respond politely"
        assert chunk.metadata == metadata

    def test_partial_values(self):
        chunk = StreamChunk(content="Hello")

        assert chunk.content == "Hello"
        assert chunk.thinking is None
        assert chunk.metadata == {}


class TestChatOptions:
    def test_default_values(self):
        options = ChatOptions()

        assert not options.enable_search
        assert options.enable_thinking
        assert options.show_thinking
        assert not options.silent

    def test_custom_values(self):
        options = ChatOptions(
            enable_search=True, enable_thinking=False, show_thinking=False, silent=True
        )

        assert options.enable_search
        assert not options.enable_thinking
        assert not options.show_thinking
        assert options.silent

    def test_partial_override(self):
        options = ChatOptions(enable_search=True, silent=True)

        assert options.enable_search
        assert options.enable_thinking  # Still default
        assert options.show_thinking  # Still default
        assert options.silent
