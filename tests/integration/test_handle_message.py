#!/usr/bin/env python3
"""Integration test for handle_message function."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import AgentRunResult
from sqlitedict import SqliteDict

from personal_assistant.app import handle_message


def create_mock_update(chat_id: int, message_text: str) -> MagicMock:
    """Create a mock Telegram Update object."""
    mock_update = MagicMock()
    mock_update.effective_user.id = chat_id
    mock_update.effective_user.first_name = "Test"
    mock_update.effective_user.last_name = "User"
    mock_update.effective_user.username = "testuser"
    mock_update.effective_chat.id = chat_id
    mock_update.message.text = message_text
    mock_update.message.reply_text = AsyncMock()
    return mock_update


def create_mock_context() -> MagicMock:
    """Create a mock Telegram Context object."""
    mock_context = MagicMock()
    mock_context.user_data = {}
    return mock_context


@pytest.fixture
def mock_user_db(tmp_path: Path):
    """Fixture that patches user_db with a temporary SQLite database."""
    with patch(
        "personal_assistant.chat.user_db",
        SqliteDict(str(tmp_path / "test.db"), autocommit=True),
    ):
        yield


@pytest.mark.asyncio
async def test_handle_message_responds_to_greeting(mock_user_db):
    """Test that handle_message processes a greeting and sends a response."""
    mock_update = create_mock_update(chat_id=123, message_text="hi")
    mock_context = create_mock_context()

    response = await handle_message(mock_update, mock_context)

    assert isinstance(response, AgentRunResult)
    assert len(response.output) > 0


@pytest.mark.asyncio
async def test_handle_message_list_reminders(mock_user_db):
    """Test that 'list reminders' calls scheduler.list and returns the result."""
    with patch("personal_assistant.scheduler.list") as mock_list:
        mock_list.return_value = ["Take medication", "Call mom"]

        mock_update = create_mock_update(chat_id=123, message_text="list reminders")
        mock_context = create_mock_context()

        response = await handle_message(mock_update, mock_context)

        mock_list.assert_called_once()
        assert isinstance(response, AgentRunResult)
        assert "Take medication" in response.output
        assert "Call mom" in response.output


@pytest.mark.asyncio
async def test_handle_message_delete_reminder(mock_user_db):
    """Test that 'delete reminder' calls scheduler.delete with the correct cron expression."""
    with patch("personal_assistant.scheduler.delete") as mock_delete:
        mock_delete.return_value = "✅ Reminder deleted successfully"

        mock_update = create_mock_update(
            chat_id=123, message_text="delete the reminder with cron 0 0 9 * * *"
        )
        mock_context = create_mock_context()

        response = await handle_message(mock_update, mock_context)

        mock_delete.assert_called_once()
        # Verify the cron expression was passed correctly (positional args)
        call_args = mock_delete.call_args
        # scheduler.delete(job_queue, chat_id, cron_expression)
        assert call_args[0][2] == "0 0 9 * * *"
        assert isinstance(response, AgentRunResult)
