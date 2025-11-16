import tempfile
from datetime import datetime
from pathlib import Path
import pytest

from llm_cli.core.message_utils import flatten_history
from llm_cli.core.session import Chat, ChatMetadata
from llm_cli.exceptions import ChatNotFoundError


class TestChatMetadata:
    def test_create_metadata(self):
        now = datetime.now()
        metadata = ChatMetadata(
            id="test-123",
            title="Test Chat",
            created_at=now,
            updated_at=now,
            model="gpt-4o",
            message_count=2,
            preview="Hello world",
            smart_title_generated=False,
        )

        assert metadata.id == "test-123"
        assert metadata.title == "Test Chat"
        assert metadata.model == "gpt-4o"
        assert metadata.message_count == 2
        assert metadata.preview == "Hello world"
        assert not metadata.smart_title_generated

    def test_to_dict(self):
        now = datetime.now()
        metadata = ChatMetadata(
            id="test-123",
            title="Test Chat",
            created_at=now,
            updated_at=now,
            model="gpt-4o",
            message_count=2,
            preview="Hello world",
        )

        data = metadata.to_dict()
        assert data["id"] == "test-123"
        assert data["title"] == "Test Chat"
        assert data["model"] == "gpt-4o"
        assert data["message_count"] == 2
        assert data["preview"] == "Hello world"
        assert "created_at" in data
        assert "updated_at" in data

    def test_from_dict(self):
        data = {
            "id": "test-123",
            "title": "Test Chat",
            "created_at": "2024-01-01T12:00:00",
            "updated_at": "2024-01-01T12:30:00",
            "model": "gpt-4o",
            "message_count": 2,
            "preview": "Hello world",
            "smart_title_generated": True,
        }

        metadata = ChatMetadata.from_dict(data)
        assert metadata.id == "test-123"
        assert metadata.title == "Test Chat"
        assert metadata.model == "gpt-4o"
        assert metadata.message_count == 2
        assert metadata.preview == "Hello world"
        assert metadata.smart_title_generated


class TestChat:
    def test_should_be_saved_with_messages(self):
        metadata = ChatMetadata(
            id="test-123",
            title="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            model="gpt-4o",
            message_count=2,
            preview="Hello",
        )

        chat = Chat(metadata=metadata)
        chat.append_user_message("Hello")
        chat.append_assistant_response("Hi there!")

        assert chat.should_be_saved()

    def test_should_not_be_saved_empty(self):
        metadata = ChatMetadata(
            id="test-123",
            title="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            model="gpt-4o",
            message_count=0,
            preview="",
        )

        chat = Chat(metadata=metadata, messages=[])
        assert not chat.should_be_saved()

    def test_should_not_be_saved_system_only(self):
        metadata = ChatMetadata(
            id="test-123",
            title="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            model="gpt-4o",
            message_count=0,
            preview="",
        )

        chat = Chat(metadata=metadata)
        chat.pending_system_prompt = "You are a helpful assistant."

        assert not chat.should_be_saved()

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the config to use temp directory
            with pytest.MonkeyPatch().context() as mp:
                mp.setattr(
                    "llm_cli.core.session.Config",
                    lambda: type("Config", (), {"chat_dir": temp_dir})(),
                )

                # Create chat
                metadata = ChatMetadata(
                    id="test-123",
                    title="Test Chat",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    model="gpt-4o",
                    message_count=2,
                    preview="Hello",
                )

                chat = Chat(metadata=metadata)
                chat.append_user_message("Hello")
                chat.append_assistant_response("Hi there!")
                chat.save()

                # Verify files exist
                chat_dir = Path(temp_dir) / "test-123"
                assert chat_dir.exists()
                assert (chat_dir / "metadata.json").exists()
                assert (chat_dir / "messages.json").exists()

                # Load chat
                loaded_chat = Chat.load("test-123")
                assert loaded_chat.metadata.id == "test-123"
                assert loaded_chat.metadata.title == "Test Chat"
                assert len(loaded_chat.messages) == 2
                history = flatten_history(loaded_chat.messages)
                assert history[0][0] == "user"
                assert history[0][1] == "Hello"

    def test_load_nonexistent_chat(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.MonkeyPatch().context() as mp:
                mp.setattr(
                    "llm_cli.core.session.Config",
                    lambda: type("Config", (), {"chat_dir": temp_dir})(),
                )

                with pytest.raises(ChatNotFoundError) as exc_info:
                    Chat.load("nonexistent-id")

                assert "Chat not found: nonexistent-id" in str(exc_info.value)
