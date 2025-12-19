"""Tests for APScheduler integration with Telegram bot."""
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, Mock, patch
from interact_with_telegram import create_scheduler


@pytest.mark.asyncio
async def test_create_scheduler_returns_scheduler():
    """Test that create_scheduler initializes APScheduler correctly."""
    # Use temporary database for test
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        scheduler = create_scheduler(f"sqlite:///{db_path}")

        # Verify scheduler exists
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        assert isinstance(scheduler, AsyncIOScheduler)

        # Verify scheduler can be started
        scheduler.start()
        assert scheduler.running

        # Cleanup
        scheduler.shutdown()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
