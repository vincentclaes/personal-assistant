import pytest
import asyncio
from datetime import datetime
from app import scheduler, schedules_store
from app import create_schedule


@pytest.mark.asyncio
async def test_create_gym_booking_schedule():
    """Test creating a recurring gym booking schedule."""
    # Ensure scheduler is started
    if not scheduler.running:
        scheduler.start()

    try:
        user_id = 99999
        chat_id = 88888

        # Create schedule for every day at 09:00 (for testing)
        schedule_id = await create_schedule(
            user_id=user_id,
            chat_id=chat_id,
            task_type="gym_booking",
            cron_hour=9,
            cron_minute=0,
            cron_day_of_week=None,  # Daily
            preferences={"preferred_hours": ["07:00", "08:00"]},
            original_request="book gym every day at 9am"
        )

        # Verify schedule created in database
        assert schedule_id is not None
        schedule = schedules_store.get_schedule(schedule_id)
        assert schedule is not None
        assert schedule["task_type"] == "gym_booking"
        assert schedule["user_id"] == user_id
        assert schedule["chat_id"] == chat_id
        assert schedule["cron_hour"] == 9
        assert schedule["cron_minute"] == 0

        # Verify job created in scheduler
        job = scheduler.get_job(schedule_id)
        assert job is not None

        # Clean up
        scheduler.remove_job(schedule_id)
        schedules_store.delete_schedule(schedule_id)

    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
