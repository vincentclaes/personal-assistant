"""Task metadata storage using sqlitedict."""
from typing import Any, Dict, Optional
from sqlitedict import SqliteDict


class TaskStore:
    """Wrapper around sqlitedict for storing task metadata.

    Stores rich context for scheduled tasks including user preferences,
    original requests, and task-specific data.
    """

    def __init__(self, db_path: str = "task_metadata.db"):
        """Initialize task store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db = SqliteDict(db_path, autocommit=True)

    def save_task(self, job_id: str, metadata: Dict[str, Any]) -> None:
        """Save task metadata.

        Args:
            job_id: APScheduler job ID
            metadata: Task metadata dictionary
        """
        self.db[job_id] = metadata

    def get_task(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task metadata.

        Args:
            job_id: APScheduler job ID

        Returns:
            Task metadata dictionary or None if not found
        """
        return self.db.get(job_id)

    def delete_task(self, job_id: str) -> None:
        """Delete task metadata.

        Args:
            job_id: APScheduler job ID
        """
        if job_id in self.db:
            del self.db[job_id]

    def list_tasks_by_user(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        """List all tasks for a specific user.

        Args:
            user_id: Telegram user ID

        Returns:
            Dictionary mapping job_id to task metadata
        """
        return {
            job_id: metadata
            for job_id, metadata in self.db.items()
            if metadata.get("user_id") == user_id
        }

    def close(self) -> None:
        """Close the database connection."""
        self.db.close()
