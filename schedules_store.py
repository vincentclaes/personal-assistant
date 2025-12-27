"""Schedule storage for cron-based task scheduling."""
import sqlite3
from typing import Optional
from datetime import datetime


class SchedulesStore:
    """Store and retrieve cron-based schedules for users."""

    def __init__(self, db_path: str):
        """
        Initialize schedules store with SQLite.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        """Create schedules table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                schedule_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                task_type TEXT NOT NULL,
                cron_minute INTEGER DEFAULT 0,
                cron_hour INTEGER NOT NULL,
                cron_day_of_week TEXT,
                preferences TEXT,
                original_request TEXT,
                created_at TEXT NOT NULL,
                enabled INTEGER DEFAULT 1
            )
        """)
        self.conn.commit()

    def create_schedule(
        self,
        schedule_id: str,
        user_id: int,
        chat_id: int,
        task_type: str,
        cron_hour: int,
        cron_minute: int = 0,
        cron_day_of_week: Optional[str] = None,
        preferences: Optional[str] = None,
        original_request: str = ""
    ) -> None:
        """
        Create a new cron-based schedule.

        Args:
            schedule_id: Unique schedule identifier
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            task_type: Type of task (e.g., 'gym_booking')
            cron_hour: Hour (0-23) for execution
            cron_minute: Minute (0-59) for execution
            cron_day_of_week: Day of week (mon, tue, wed, thu, fri, sat, sun) or None for daily
            preferences: JSON string of task preferences
            original_request: User's original natural language request
        """
        self.conn.execute("""
            INSERT INTO schedules
            (schedule_id, user_id, chat_id, task_type, cron_hour, cron_minute,
             cron_day_of_week, preferences, original_request, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            schedule_id, user_id, chat_id, task_type, cron_hour, cron_minute,
            cron_day_of_week, preferences, original_request, datetime.now().isoformat()
        ))
        self.conn.commit()

    def get_schedule(self, schedule_id: str) -> Optional[dict]:
        """
        Get a schedule by ID.

        Args:
            schedule_id: Schedule identifier

        Returns:
            Schedule dictionary or None if not found
        """
        cursor = self.conn.execute(
            "SELECT * FROM schedules WHERE schedule_id = ?",
            (schedule_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_schedules_for_user(self, user_id: int) -> list[dict]:
        """
        List all enabled schedules for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            List of schedule dictionaries
        """
        cursor = self.conn.execute(
            "SELECT * FROM schedules WHERE user_id = ? AND enabled = 1",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def list_all_enabled_schedules(self) -> list[dict]:
        """
        List all enabled schedules across all users.

        Returns:
            List of schedule dictionaries
        """
        cursor = self.conn.execute(
            "SELECT * FROM schedules WHERE enabled = 1"
        )
        return [dict(row) for row in cursor.fetchall()]

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: Schedule identifier

        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.execute(
            "DELETE FROM schedules WHERE schedule_id = ?",
            (schedule_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def disable_schedule(self, schedule_id: str) -> bool:
        """
        Disable a schedule (soft delete).

        Args:
            schedule_id: Schedule identifier

        Returns:
            True if disabled, False if not found
        """
        cursor = self.conn.execute(
            "UPDATE schedules SET enabled = 0 WHERE schedule_id = ?",
            (schedule_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()
