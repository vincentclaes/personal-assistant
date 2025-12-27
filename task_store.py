"""Task metadata storage using sqlitedict."""
from typing import Any, Optional
from sqlitedict import SqliteDict


class TaskStore:
    """Store and retrieve task metadata for scheduled jobs."""

    def __init__(self, db_path: str):
        """
        Initialize task store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db = SqliteDict(db_path, autocommit=True)

    def save_task(self, job_id: str, metadata: dict[str, Any]) -> None:
        """
        Save task metadata.

        Args:
            job_id: APScheduler job ID
            metadata: Task metadata dictionary
        """
        self.db[job_id] = metadata

    def get_task(self, job_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve task metadata.

        Args:
            job_id: APScheduler job ID

        Returns:
            Task metadata or None if not found
        """
        return self.db.get(job_id)

    def delete_task(self, job_id: str) -> None:
        """
        Delete task metadata.

        Args:
            job_id: APScheduler job ID
        """
        if job_id in self.db:
            del self.db[job_id]

    def list_tasks_for_user(self, user_id: int) -> list[tuple[str, dict[str, Any]]]:
        """
        List all tasks for a specific user.

        Args:
            user_id: Telegram user ID

        Returns:
            List of (job_id, metadata) tuples
        """
        results = []
        for job_id, metadata in self.db.items():
            if metadata.get("user_id") == user_id:
                results.append((job_id, metadata))
        return results

    def close(self) -> None:
        """Close database connection."""
        self.db.close()
