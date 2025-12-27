import tempfile
import os
from task_store import TaskStore

def test_store_and_retrieve_task_metadata():
    """Test storing and retrieving task metadata."""
    # Use temp file for test database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        store = TaskStore(db_path)

        # Store task metadata
        job_id = "test_job_123"
        metadata = {
            "task_type": "gym_booking",
            "user_id": 12345,
            "chat_id": 67890,
            "original_request": "book gym every Monday at 7am",
            "preferences": {
                "preferred_hours": ["07:00", "08:00"],
            },
            "created_at": "2025-12-27T10:00:00"
        }

        store.save_task(job_id, metadata)

        # Retrieve and verify
        retrieved = store.get_task(job_id)
        assert retrieved is not None
        assert retrieved["task_type"] == "gym_booking"
        assert retrieved["user_id"] == 12345
        assert retrieved["preferences"]["preferred_hours"] == ["07:00", "08:00"]

        # Clean up
        store.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
