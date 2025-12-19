"""Pydantic AI tools for scheduling tasks."""
import os
from datetime import datetime
from typing import Any, Callable, Dict
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from task_store import TaskStore


def create_schedule_tool(
    scheduler: AsyncIOScheduler,
    task_store: TaskStore,
    timezone: str = None
) -> Callable:
    """Create tool for scheduling tasks.

    Args:
        scheduler: APScheduler instance
        task_store: TaskStore instance
        timezone: Timezone string for scheduling (defaults to env var or Europe/Brussels)

    Returns:
        Tool function for creating schedules
    """
    # Use environment variable if timezone not provided
    if timezone is None:
        timezone = os.getenv('TIMEZONE', 'Europe/Brussels')

    def tool(
        task_type: str,
        schedule_time: datetime,
        task_params: Dict[str, Any],
        is_recurring: bool = False,
        cron_pattern: Dict[str, Any] = None
    ) -> str:
        """Create a scheduled task.

        Args:
            task_type: Type of task ('reminder' or 'gym_booking')
            schedule_time: When to execute (for one-time tasks)
            task_params: Task-specific parameters and preferences
            is_recurring: Whether task repeats
            cron_pattern: Cron pattern for recurring tasks (e.g., {'day_of_week': 'mon', 'hour': 7})

        Returns:
            Confirmation message with job ID
        """
        logger.info(f"Creating {task_type} schedule")

        try:
            # Determine trigger
            if is_recurring and cron_pattern:
                trigger = CronTrigger(
                    timezone=timezone,
                    **cron_pattern
                )
            else:
                trigger = DateTrigger(
                    run_date=schedule_time,
                    timezone=timezone
                )

            # Determine handler function name based on task type
            if task_type == "reminder":
                func_id = "send_reminder"
            elif task_type == "gym_booking":
                func_id = "gym_booking"
            else:
                return f"Error: Unknown task type '{task_type}'"

            # Add job to scheduler (using v3 API)
            job = scheduler.add_job(
                func=func_id,  # Will be resolved when handlers are registered
                trigger=trigger,
                id=None,  # Let scheduler generate ID
                args=[],  # Job ID will be passed by scheduler
            )

            job_id = job.id

            # Store task metadata
            metadata = {
                "task_type": task_type,
                "user_id": task_params.get("user_id"),
                "chat_id": task_params.get("chat_id"),
                "preferences": task_params,
                "created_at": datetime.now().isoformat(),
                "is_recurring": is_recurring
            }

            task_store.save_task(job_id, metadata)

            logger.info(f"Created schedule with job ID: {job_id}")
            return f"✓ Schedule created (ID: {job_id})"

        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            return f"Error creating schedule: {str(e)}"

    return tool


def list_schedules_tool(task_store: TaskStore) -> Callable:
    """Create tool for listing user's schedules.

    Args:
        task_store: TaskStore instance

    Returns:
        Tool function for listing schedules
    """
    def tool(user_id: int) -> str:
        """List all schedules for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            Formatted list of schedules
        """
        tasks = task_store.list_tasks_by_user(user_id)

        if not tasks:
            return "You have no scheduled tasks."

        lines = ["Your scheduled tasks:"]
        for job_id, metadata in tasks.items():
            task_type = metadata.get("task_type", "unknown")
            is_recurring = metadata.get("is_recurring", False)
            recurrence = "recurring" if is_recurring else "one-time"
            lines.append(f"- {task_type} ({recurrence}) [ID: {job_id}]")

        return "\n".join(lines)

    return tool


def cancel_schedule_tool(
    scheduler: AsyncIOScheduler,
    task_store: TaskStore
) -> Callable:
    """Create tool for canceling schedules.

    Args:
        scheduler: APScheduler instance
        task_store: TaskStore instance

    Returns:
        Tool function for canceling schedules
    """
    def tool(job_id: str) -> str:
        """Cancel a scheduled task.

        Args:
            job_id: Job ID to cancel

        Returns:
            Confirmation message
        """
        try:
            # Remove from scheduler
            scheduler.remove_job(job_id)

            # Remove metadata
            task_store.delete_task(job_id)

            logger.info(f"Cancelled schedule: {job_id}")
            return f"✓ Schedule cancelled (ID: {job_id})"

        except Exception as e:
            logger.error(f"Error cancelling schedule: {e}")
            return f"Error cancelling schedule: {str(e)}"

    return tool
