"""Tests for task execution handlers."""
import tempfile
import pytest
from unittest.mock import AsyncMock, Mock, patch
from task_handlers import send_reminder_handler
from task_store import TaskStore


@pytest.mark.asyncio
async def test_send_reminder_handler_sends_message():
    """Test that reminder handler sends Telegram message."""
    # Setup test database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        store = TaskStore(db_path)
        job_id = "test_reminder_123"

        # Store test reminder metadata
        store.save_task(job_id, {
            "task_type": "reminder",
            "chat_id": 12345,
            "preferences": {"message": "test reminder message"}
        })

        # Mock Telegram bot
        mock_bot = Mock()
        mock_bot.send_message = AsyncMock()

        # Create handler with dependencies
        handler = send_reminder_handler(bot=mock_bot, task_store=store)

        # Execute handler
        await handler(job_id)

        # Verify message was sent
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert call_args[1]['chat_id'] == 12345
        assert "test reminder message" in call_args[1]['text']

        store.close()
    finally:
        import os
        if os.path.exists(db_path):
            os.unlink(db_path)
