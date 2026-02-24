import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from llm_cli.config.settings import Config
from llm_cli.core.message_utils import flatten_history
from llm_cli.core.chat_repository import ChatRepository
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
            smart_title_generated=False,
        )

        assert metadata.id == "test-123"
        assert metadata.title == "Test Chat"
        assert metadata.model == "gpt-4o"
        assert metadata.message_count == 2
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
        )

        data = metadata.to_dict()
        assert data["id"] == "test-123"
        assert data["title"] == "Test Chat"
        assert data["model"] == "gpt-4o"
        assert data["message_count"] == 2
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
        assert metadata.smart_title_generated
        assert not hasattr(metadata, "preview")


class TestChat:
    def test_should_be_saved_with_messages(self):
        metadata = ChatMetadata(
            id="test-123",
            title="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            model="gpt-4o",
            message_count=2,
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
        )

        chat = Chat(metadata=metadata)
        chat.pending_system_prompt = "You are a helpful assistant."

        assert not chat.should_be_saved()


class TestChatRepository:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ChatRepository(Config(chat_dir=temp_dir, vim_mode=False))

            metadata = ChatMetadata(
                id="test-123",
                title="Test Chat",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                model="gpt-4o",
                message_count=2,
            )

            chat = Chat(metadata=metadata)
            chat.append_user_message("Hello")
            chat.append_assistant_response("Hi there!")
            repository.save_chat(chat)

            chat_dir = Path(temp_dir) / "test-123"
            assert chat_dir.exists()
            assert (chat_dir / "metadata.json").exists()
            assert (chat_dir / "messages.json").exists()

            loaded_chat = repository.load_chat("test-123")
            assert loaded_chat.metadata.id == "test-123"
            assert loaded_chat.metadata.title == "Test Chat"
            assert len(loaded_chat.messages) == 2
            history = flatten_history(loaded_chat.messages)
            assert history[0][0] == "user"
            assert history[0][1] == "Hello"

    def test_load_nonexistent_chat(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ChatRepository(Config(chat_dir=temp_dir, vim_mode=False))

            with pytest.raises(ChatNotFoundError) as exc_info:
                repository.load_chat("nonexistent-id")

            assert "Chat not found: nonexistent-id" in str(exc_info.value)

    def test_try_load_chat_returns_none_and_reports_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ChatRepository(Config(chat_dir=temp_dir, vim_mode=False))
            on_error = Mock()

            loaded_chat = repository.try_load_chat("nonexistent-id", on_error=on_error)

            assert loaded_chat is None
            on_error.assert_called_once()
            assert on_error.call_args[0][0] == "nonexistent-id"
            assert isinstance(on_error.call_args[0][1], ChatNotFoundError)

    def test_list_chat_metadata_sorts_and_skips_unreadable_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ChatRepository(Config(chat_dir=temp_dir, vim_mode=False))

            older = ChatMetadata(
                id="older",
                title="Older Chat",
                created_at=datetime.fromisoformat("2024-01-01T10:00:00"),
                updated_at=datetime.fromisoformat("2024-01-01T10:00:00"),
                model="gpt-4o",
                message_count=2,
            )
            newer = ChatMetadata(
                id="newer",
                title="Newer Chat",
                created_at=datetime.fromisoformat("2024-01-02T10:00:00"),
                updated_at=datetime.fromisoformat("2024-01-02T10:00:00"),
                model="gpt-4o",
                message_count=4,
            )

            for metadata in (older, newer):
                chat_dir = repository.chat_path(metadata.id)
                chat_dir.mkdir(parents=True)
                (chat_dir / "metadata.json").write_text(json.dumps(metadata.to_dict()))

            bad_dir = repository.chat_path("broken")
            bad_dir.mkdir(parents=True)
            (bad_dir / "metadata.json").write_text("{not json")

            on_unreadable_metadata = Mock()

            chats = repository.list_chat_metadata(
                on_unreadable_metadata=on_unreadable_metadata
            )

            assert [chat.id for chat in chats] == ["newer", "older"]
            on_unreadable_metadata.assert_called_once()
            assert on_unreadable_metadata.call_args[0][0] == "broken"

    def test_list_chat_metadata_reports_root_read_error(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = ChatRepository(Config(chat_dir=temp_dir, vim_mode=False))
            on_root_read_error = Mock()

            def raise_oserror(self):
                raise OSError("boom")

            monkeypatch.setattr(Path, "iterdir", raise_oserror)

            chats = repository.list_chat_metadata(on_root_read_error=on_root_read_error)

            assert chats == []
            on_root_read_error.assert_called_once()
            assert on_root_read_error.call_args[0][0] == repository.chat_root
