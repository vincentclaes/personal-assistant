import tempfile
import os
from schedules_store import SchedulesStore


def test_create_and_retrieve_schedule():
    """Test creating and retrieving a cron-based schedule."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        store = SchedulesStore(db_path)

        # Create a schedule
        store.create_schedule(
            schedule_id="test_schedule_1",
            user_id=12345,
            chat_id=67890,
            task_type="gym_booking",
            cron_hour=7,
            cron_minute=0,
            cron_day_of_week="mon",
            preferences='{"preferred_hours": ["07:00", "08:00"]}',
            original_request="book gym every Monday at 7am"
        )

        # Retrieve and verify
        schedule = store.get_schedule("test_schedule_1")
        assert schedule is not None
        assert schedule["user_id"] == 12345
        assert schedule["chat_id"] == 67890
        assert schedule["task_type"] == "gym_booking"
        assert schedule["cron_hour"] == 7
        assert schedule["cron_minute"] == 0
        assert schedule["cron_day_of_week"] == "mon"
        assert schedule["enabled"] == 1

        # List schedules for user
        schedules = store.list_schedules_for_user(12345)
        assert len(schedules) == 1
        assert schedules[0]["schedule_id"] == "test_schedule_1"

        # Clean up
        store.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
