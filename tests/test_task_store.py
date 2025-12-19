"""Tests for task metadata store."""
import os
import tempfile
from task_store import TaskStore


def test_store_and_retrieve_task_metadata():
    """Test storing and retrieving task metadata."""
    # Use temporary file for test database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        store = TaskStore(db_path)

        # Store task metadata
        job_id = "test_job_123"
        metadata = {
            "task_type": "reminder",
            "user_id": 12345,
            "chat_id": 67890,
            "original_request": "remind me to call mom",
            "preferences": {"message": "call mom"},
            "created_at": "2025-12-19T10:30:00"
        }

        store.save_task(job_id, metadata)

        # Retrieve task metadata
        retrieved = store.get_task(job_id)

        assert retrieved is not None
        assert retrieved["task_type"] == "reminder"
        assert retrieved["user_id"] == 12345
        assert retrieved["chat_id"] == 67890
        assert retrieved["preferences"]["message"] == "call mom"

        store.close()
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
