"""Tests for Pydantic AI agent tools."""
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock
from agent_tools import create_schedule_tool
from task_store import TaskStore


def test_create_schedule_tool_creates_job():
    """Test that create_schedule tool creates APScheduler job."""
    # Setup test database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        store = TaskStore(db_path)

        # Mock scheduler
        mock_scheduler = Mock()
        mock_scheduler.add_job = Mock(return_value=Mock(id="job_123"))

        # Create tool
        tool = create_schedule_tool(
            scheduler=mock_scheduler,
            task_store=store
        )

        # Execute tool
        result = tool(
            task_type="reminder",
            schedule_time=datetime.now() + timedelta(hours=1),
            task_params={
                "chat_id": 12345,
                "user_id": 67890,
                "message": "test reminder"
            }
        )

        # Verify job was created
        mock_scheduler.add_job.assert_called_once()

        # Verify result contains job_id
        assert "job_123" in result

        # Verify metadata was saved
        metadata = store.get_task("job_123")
        assert metadata is not None
        assert metadata["task_type"] == "reminder"

        store.close()
    finally:
        import os
        if os.path.exists(db_path):
            os.unlink(db_path)
