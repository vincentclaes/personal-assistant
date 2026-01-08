#!/usr/bin/env python3
"""Integration test for handle_message function."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import AgentRunResult
from sqlitedict import SqliteDict

from personal_assistant.app import handle_message


@pytest.mark.asyncio
async def test_handle_message_responds_to_greeting(tmp_path: Path):
    """Test that handle_message processes a greeting and sends a response."""
    with patch(
        "personal_assistant.app.user_db",
        SqliteDict(str(tmp_path / "test.db"), autocommit=True),
    ):
        # Mock Telegram Update (external boundary)
        mock_update = MagicMock()
        mock_update.effective_user.id = 123
        mock_update.effective_user.first_name = "Test"
        mock_update.effective_user.last_name = "User"
        mock_update.effective_user.username = "testuser"
        mock_update.effective_chat.id = 123
        mock_update.message.text = "hi"
        mock_update.message.reply_text = AsyncMock()

        # Mock Telegram Context (external boundary)
        mock_context = MagicMock()
        mock_context.user_data = {}

        response = await handle_message(mock_update, mock_context)

        assert isinstance(response, AgentRunResult)
        assert len(response.output) > 0
