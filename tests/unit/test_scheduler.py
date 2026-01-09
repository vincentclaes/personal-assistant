#!/usr/bin/env python3
"""Unit test for APScheduler reminder scheduling with Telegram Application."""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from telegram.ext import Application

from personal_assistant.app import create_application
from personal_assistant.scheduler import (
    delete_reminder,
    list_reminders,
    schedule_cron_job,
)


@pytest_asyncio.fixture
async def application() -> AsyncGenerator[Application, None]:
    """
    Fixture to create and initialize the Telegram Application.

    Yields:
        Initialized Application instance

    Cleanup:
        Shuts down the application after the test
    """
    app = create_application()
    await app.initialize()
    yield app
    await app.shutdown()


@pytest.mark.asyncio
async def test_schedule_reminder_with_application(application: Application):
    """Test scheduling a reminder using the Telegram Application's job_queue."""
    job_queue = application.job_queue
    chat_id = 123456
    message = "Daily standup reminder"
    cron_expression = "0 0 9 * * *"

    # Schedule using the function from scheduler module
    result = schedule_cron_job(
        job_queue=job_queue,
        chat_id=chat_id,
        message=message,
        cron_expression=cron_expression,
    )

    # Verify confirmation message returned
    assert "✅ Recurring reminder scheduled:" in result
    assert message in result
    assert cron_expression in result

    # Verify job is retrievable from scheduler by the id
    job_id = f"reminder_{chat_id}_{cron_expression.replace(' ', '_')}"
    scheduler = job_queue.scheduler
    aps_job = scheduler.get_job(job_id)
    assert aps_job is not None


@pytest.mark.asyncio
async def test_list_reminders(application: Application):
    """Test listing all reminders for a chat_id."""
    job_queue = application.job_queue
    chat_id = 123456

    # Schedule a reminder
    schedule_cron_job(
        job_queue=job_queue,
        chat_id=chat_id,
        message="Daily standup",
        cron_expression="0 0 9 * * *",
    )

    # List reminders
    reminders = list_reminders(job_queue, chat_id)

    # Verify reminder is in the list
    assert len(reminders) == 1
    assert "Daily standup" in reminders[0]


@pytest.mark.asyncio
async def test_delete_reminder(application: Application):
    """Test deleting a specific reminder by cron expression."""
    job_queue = application.job_queue
    chat_id = 123456
    cron_expression = "0 0 9 * * *"

    # Schedule a reminder
    schedule_cron_job(
        job_queue=job_queue,
        chat_id=chat_id,
        message="Daily standup",
        cron_expression=cron_expression,
    )

    # Verify it exists
    reminders = list_reminders(job_queue, chat_id)
    assert len(reminders) == 1

    # Delete the reminder
    result = delete_reminder(job_queue, chat_id, cron_expression)

    # Verify it was deleted
    assert "deleted" in result.lower() or "removed" in result.lower()
    reminders_after = list_reminders(job_queue, chat_id)
    assert len(reminders_after) == 0
