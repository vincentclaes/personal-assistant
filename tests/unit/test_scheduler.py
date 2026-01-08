#!/usr/bin/env python3
"""Unit test for APScheduler reminder scheduling with Telegram Application."""

import pytest
import pytest_asyncio
from collections.abc import AsyncGenerator
from telegram.ext import Application

from personal_assistant.app import create_application, _schedule_cron_job


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

    # Schedule using the private function (same as production code)
    result = _schedule_cron_job(
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
