"""Test reminder scheduling functionality."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

import app
import database
import scheduler
from scheduler import add_date_job, shutdown_scheduler, get_scheduler


@pytest.fixture(autouse=True)
def test_database():
    """Use a temporary database for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "test_reminders.db"

        # Patch the DB_PATH so scheduler picks it up
        with patch.object(database, 'DB_PATH', str(test_db_path)):
            # Reset the singleton scheduler
            scheduler._scheduler = None

            yield

            # Cleanup
            shutdown_scheduler()
            scheduler._scheduler = None


# Module-level tracking for test verification
_reminder_called = False
_reminder_args = None


# Module-level reminder function for testing (needs to be at module level for pickle)
async def send_reminder(chat_id: int, message: str):
    """Simple test reminder function."""
    global _reminder_called, _reminder_args
    print(f"✅ test_send_reminder EXECUTED! chat_id={chat_id}, message={message}")
    _reminder_called = True
    _reminder_args = (chat_id, message)
    return f"Reminder sent: {message}"


@pytest.mark.asyncio
async def test_schedule_reminder_creates_job():
    """Test that we can schedule a reminder and it creates a job with correct parameters."""
    import asyncio
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from scheduler import start_scheduler

    global _reminder_called, _reminder_args

    # Reset tracking flags
    _reminder_called = False
    _reminder_args = None

    # Start the scheduler in the running event loop
    start_scheduler()

    # Schedule reminder for 2 seconds in the future
    user_chat_id = 12345
    reminder_message = "Call dentist"
    run_time = datetime.now(ZoneInfo('Europe/Brussels')) + timedelta(seconds=2)

    job_id = add_date_job(
        func=send_reminder,
        run_date=run_time,
        job_id="reminder_test_1",
        kwargs={"chat_id": user_chat_id, "message": reminder_message}
    )

    # Verify job was created
    sched = get_scheduler()
    jobs = sched.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "reminder_test_1"
    assert jobs[0].id == job_id
    assert jobs[0].func == send_reminder

    # Wait for the job to execute (2 seconds + 1 second buffer)
    print("Waiting for reminder to execute...")
    await asyncio.sleep(3)

    # Verify the reminder function was actually called
    assert _reminder_called, "Reminder function was not called!"
    assert _reminder_args == (user_chat_id, reminder_message), f"Expected args ({user_chat_id}, {reminder_message}), got {_reminder_args}"

    print("✅ Test passed - reminder function was called with correct arguments!")
