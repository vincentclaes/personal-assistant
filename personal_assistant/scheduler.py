#!/usr/bin/env python3
"""Scheduler module for managing reminders and scheduled jobs."""

import datetime
from zoneinfo import ZoneInfo

from apscheduler.job import Job as APSJob
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from telegram.ext import Application, ContextTypes, JobQueue
from telegram.ext._jobqueue import Job


class PTBSQLiteJobStore(SQLAlchemyJobStore):
    """SQLite jobstore that makes telegram.ext.Job class storable."""

    def __init__(self, application: Application, url: str = "sqlite:///bot.db") -> None:
        """Initialize with Application instance and SQLite database path.

        Args:
            application: Application instance for CallbackContext recreation
            url: SQLite database URL (default: sqlite:///bot.db)
        """
        self.application = application
        super().__init__(url=url)

    @staticmethod
    def _prepare_job(job: APSJob) -> APSJob:
        """Prepare job for storage by extracting Telegram-specific data."""
        prepped_job = APSJob.__new__(APSJob)
        prepped_job.__setstate__(job.__getstate__())
        tg_job = Job.from_aps_job(job)
        prepped_job.args = (
            tg_job.name,
            tg_job.data,
            tg_job.chat_id,
            tg_job.user_id,
            tg_job.callback,
        )
        return prepped_job

    def _restore_job(self, job: APSJob) -> APSJob:
        """Restore Telegram-specific job data after loading from database."""
        name, data, chat_id, user_id, callback = job.args
        tg_job = Job(
            callback=callback,
            chat_id=chat_id,
            user_id=user_id,
            name=name,
            data=data,
        )
        job._modify(
            args=(
                self.application.job_queue,
                tg_job,
            )
        )
        return job

    def add_job(self, job: APSJob) -> None:
        """Persist newly added job to database."""
        job = self._prepare_job(job)
        super().add_job(job)

    def update_job(self, job: APSJob) -> None:
        """Update existing job in database."""
        job = self._prepare_job(job)
        super().update_job(job)

    def _reconstitute_job(self, job_state: bytes) -> APSJob:
        """Reconstruct job from pickled state retrieved from database."""
        job: APSJob = super()._reconstitute_job(job_state)
        return self._restore_job(job)


def schedule_cron_job(
    job_queue: JobQueue,
    chat_id: int,
    message: str,
    cron_expression: str,
    timezone_str: str = "Europe/Brussels",
    start_datetime: datetime.datetime | None = None,
    end_datetime: datetime.datetime | None = None,
) -> str:
    """
    Schedule a cron job on the job queue.

    Args:
        job_queue: Telegram JobQueue instance
        chat_id: Chat ID to send reminders to
        message: Reminder message
        cron_expression: 6-field cron string (second minute hour day month day_of_week)
        timezone_str: Timezone for the schedule
        start_datetime: Optional start time for the schedule
        end_datetime: Optional end time for the schedule

    Returns:
        Confirmation message with schedule details
    """
    # Parse cron expression
    parts = cron_expression.split()
    if len(parts) != 6:
        return "❌ Invalid cron expression. Must have exactly 6 fields: second minute hour day month day_of_week"

    second, minute, hour, day, month, day_of_week = parts

    # Set timezone
    tz = ZoneInfo(timezone_str)

    # Create trigger with all parameters
    trigger = CronTrigger(
        second=second,
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        start_date=start_datetime,
        end_date=end_datetime,
        timezone=tz,
    )

    job_id = f"reminder_{chat_id}_{cron_expression.replace(' ', '_')}"
    job_queue.run_custom(
        callback=reminder_callback,
        job_kwargs={
            "trigger": trigger,
            "id": job_id,
            "replace_existing": True,
        },
        name=job_id,
        chat_id=chat_id,
        data={"message": message},
    )

    # Build confirmation message
    details = "✅ Recurring reminder scheduled:\n"
    details += f"📝 Message: '{message}'\n"
    details += f"⏱️ Schedule: {cron_expression}\n"
    details += f"🌍 Timezone: {timezone_str}\n"
    if start_datetime:
        details += f"▶️ Starts: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n"
    else:
        details += "▶️ Starts: Immediately\n"
    if end_datetime:
        details += f"⏹️ Ends: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n"
    else:
        details += "⏹️ Ends: Never (runs indefinitely)\n"

    return details


def list(job_queue: JobQueue, chat_id: int) -> list[str]:
    """
    List all reminders for a specific chat_id.

    Args:
        job_queue: Telegram JobQueue instance
        chat_id: Chat ID to filter reminders by

    Returns:
        List of strings describing each reminder
    """
    reminders = []

    # Use regex pattern to filter jobs by chat_id in the job name
    pattern = f"_{chat_id}_"
    jobs = job_queue.jobs(pattern=pattern)

    for job in jobs:
        message = job.data.get("message", "N/A")
        reminders.append(f"{message}")

    return reminders


def delete(job_queue: JobQueue, chat_id: int, cron_expression: str) -> str:
    """
    Delete a specific reminder by its cron expression.

    Args:
        job_queue: Telegram JobQueue instance
        chat_id: Chat ID of the reminder owner
        cron_expression: The cron expression that identifies the reminder

    Returns:
        Confirmation message indicating success or failure
    """
    # Build the job ID using the same pattern as when scheduling
    job_id = f"reminder_{chat_id}_{cron_expression.replace(' ', '_')}"

    # Get the scheduler and try to remove the job
    scheduler = job_queue.scheduler
    job = scheduler.get_job(job_id)

    if job:
        job.remove()
        return f"✅ Reminder deleted successfully (ID: {job_id})"
    else:
        return "❌ No reminder found with the specified schedule"


def schedule_agent_task_cron(
    job_queue: JobQueue,
    chat_id: int,
    prompt: str,
    chat_with_user: bool,
    cron_expression: str,
    callback,
    timezone_str: str = "Europe/Brussels",
    start_datetime: datetime.datetime | None = None,
    end_datetime: datetime.datetime | None = None,
) -> str:
    """
    Schedule an agent task to run on a cron schedule.

    Args:
        job_queue: Telegram JobQueue instance
        chat_id: Chat ID to send results to
        prompt: Task prompt for the agent (e.g., "Book a gym session tomorrow at 6pm")
        chat_with_user: Whether the scheduled agent should be allowed to ask the user questions.
        cron_expression: 6-field cron string (second minute hour day month day_of_week)
        callback: Async callback function to execute when the job triggers
        timezone_str: Timezone for the schedule
        start_datetime: Optional start time for the schedule
        end_datetime: Optional end time for the schedule

    Returns:
        Confirmation message with schedule details
    """
    # Parse cron expression
    parts = cron_expression.split()
    if len(parts) != 6:
        return "❌ Invalid cron expression. Must have exactly 6 fields: second minute hour day month day_of_week"

    second, minute, hour, day, month, day_of_week = parts

    # Set timezone
    tz = ZoneInfo(timezone_str)

    # Create trigger with all parameters
    trigger = CronTrigger(
        second=second,
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        start_date=start_datetime,
        end_date=end_datetime,
        timezone=tz,
    )

    job_id = f"agent_task_{chat_id}_{cron_expression.replace(' ', '_')}"
    job_queue.run_custom(
        callback=callback,
        job_kwargs={
            "trigger": trigger,
            "id": job_id,
            "replace_existing": True,
        },
        name=job_id,
        chat_id=chat_id,
        data={"message": prompt, "chat_id": chat_id, "chat_with_user": chat_with_user},
    )

    # Build confirmation message
    details = "✅ Agent task scheduled:\n"
    details += f"📝 Prompt: '{prompt}'\n"
    details += f"⏱️ Schedule: {cron_expression}\n"
    details += f"🌍 Timezone: {timezone_str}\n"
    if start_datetime:
        details += f"▶️ Starts: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n"
    else:
        details += "▶️ Starts: Immediately\n"
    if end_datetime:
        details += f"⏹️ Ends: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n"
    else:
        details += "⏹️ Ends: Never (runs indefinitely)\n"

    return details


async def reminder_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    JobQueue callback for sending reminders.

    This function is called by the Telegram JobQueue when a reminder is due.
    It accesses the message and chat_id from the job's context.

    Args:
        context: Telegram context containing job data and bot instance
    """
    job = context.job
    message = job.data["message"]
    chat_id = job.chat_id

    logger.info(f"⏰ REMINDER TRIGGERED for chat_id={chat_id}: {message}")
    formatted_message = f"🔔 Reminder: {message}"

    try:
        await context.bot.send_message(chat_id=chat_id, text=formatted_message)
        logger.info("✅ Reminder sent successfully")
    except Exception as e:
        logger.info(f"❌ Error sending reminder: {e}")
