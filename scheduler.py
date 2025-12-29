"""
Reusable APScheduler module for personal assistant.

Provides a singleton scheduler instance that can be imported and used
by other modules to add jobs with SQLite persistence.
"""

import asyncio
import os
from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from dotenv import load_dotenv
from loguru import logger

from database import DB_PATH

# Load environment variables
load_dotenv()

# Configuration
TIMEZONE = ZoneInfo(os.getenv('TIMEZONE', 'Europe/Brussels'))

# Singleton scheduler instance
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """
    Get or create the singleton scheduler instance.

    Returns:
        The shared AsyncIOScheduler instance
    """
    global _scheduler

    if _scheduler is None:
        jobstores = {
            'default': SQLAlchemyJobStore(url=f'sqlite:///{DB_PATH}')
        }
        _scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            timezone=TIMEZONE
        )
        logger.info(f"Scheduler initialized with SQLite persistence ({DB_PATH})")

    return _scheduler


def start_scheduler() -> None:
    """Start the scheduler if not already running."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler shutdown")


def add_cron_job(
    func: Callable,
    cron_expression: str = None,
    job_id: str = None,
    replace_existing: bool = True,
    args: list = None,
    kwargs: dict = None,
    **cron_kwargs
) -> str:
    """
    Add a cron-based recurring job.

    Args:
        func: The function to execute
        cron_expression: Cron expression string (e.g., '0 7 * * mon')
        job_id: Optional job ID (generated if not provided)
        replace_existing: Replace job if ID exists
        args: Positional arguments for func
        kwargs: Keyword arguments for func
        **cron_kwargs: CronTrigger arguments (minute, hour, day_of_week, etc.)

    Returns:
        The job ID
    """
    scheduler = get_scheduler()

    if cron_expression:
        # Parse cron expression if provided
        parts = cron_expression.split()
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone=TIMEZONE
            )
        else:
            raise ValueError("Cron expression must have 5 parts: minute hour day month day_of_week")
    else:
        # Use kwargs for trigger
        trigger = CronTrigger(timezone=TIMEZONE, **cron_kwargs)

    job = scheduler.add_job(
        func,
        trigger=trigger,
        id=job_id,
        replace_existing=replace_existing,
        args=args or [],
        kwargs=kwargs or {}
    )

    logger.info(f"Added cron job {job.id}")
    return job.id


def add_date_job(
    func: Callable,
    run_date: datetime,
    job_id: str = None,
    replace_existing: bool = True,
    args: list = None,
    kwargs: dict = None
) -> str:
    """
    Add a one-time job at a specific date/time.

    Args:
        func: The function to execute
        run_date: When to run the job
        job_id: Optional job ID (generated if not provided)
        replace_existing: Replace job if ID exists
        args: Positional arguments for func
        kwargs: Keyword arguments for func

    Returns:
        The job ID
    """
    scheduler = get_scheduler()

    job = scheduler.add_job(
        func,
        trigger=DateTrigger(run_date=run_date, timezone=TIMEZONE),
        id=job_id,
        replace_existing=replace_existing,
        args=args or [],
        kwargs=kwargs or {}
    )

    logger.info(f"Added one-time job {job.id} for {run_date}")
    return job.id


def remove_job(job_id: str) -> bool:
    """
    Remove a scheduled job.

    Args:
        job_id: The job identifier

    Returns:
        True if job was removed, False if not found
    """
    scheduler = get_scheduler()
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Removed job {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to remove job {job_id}: {e}")
        return False


def list_jobs() -> list:
    """
    List all scheduled jobs.

    Returns:
        List of job objects
    """
    scheduler = get_scheduler()
    return scheduler.get_jobs()


def add_user_job(
    user_id: int,
    job_type: str,
    unique_id: str,
    func: Callable,
    args: list = None,
    kwargs: dict = None,
    **cron_kwargs
) -> str:
    """
    Add a cron job for a specific user with namespaced job ID.

    Args:
        user_id: Telegram user ID
        job_type: Type of job (e.g., 'reminder', 'gym_check')
        unique_id: Unique identifier for this specific job (e.g., 'morning', '9am')
        func: The function to execute
        args: Positional arguments for func
        kwargs: Keyword arguments for func
        **cron_kwargs: CronTrigger arguments (minute, hour, day_of_week, etc.)

    Returns:
        The namespaced job ID (format: user_{user_id}_{job_type}_{unique_id})
    """
    job_id = f"user_{user_id}_{job_type}_{unique_id}"
    return add_cron_job(
        func=func,
        job_id=job_id,
        replace_existing=True,
        args=args,
        kwargs=kwargs,
        **cron_kwargs
    )


def get_user_jobs(user_id: int) -> list:
    """
    Get all scheduled jobs for a specific user.

    Args:
        user_id: Telegram user ID

    Returns:
        List of job objects for the user
    """
    all_jobs = list_jobs()
    user_prefix = f"user_{user_id}_"
    return [job for job in all_jobs if job.id.startswith(user_prefix)]


def remove_user_job(user_id: int, job_type: str, unique_id: str) -> bool:
    """
    Remove a specific job for a user.

    Args:
        user_id: Telegram user ID
        job_type: Type of job to remove
        unique_id: Unique identifier of the job

    Returns:
        True if job was removed, False if not found
    """
    job_id = f"user_{user_id}_{job_type}_{unique_id}"
    return remove_job(job_id)


# Demo task for testing
async def execute_recurring_task(task_name: str) -> None:
    """Execute a recurring task."""
    logger.info(f"⚡ Recurring task: {task_name} at {datetime.now().strftime('%H:%M:%S')}")


async def main():
    """Demo usage of the scheduler module."""
    # Start the scheduler
    start_scheduler()

    try:
        # Add a cron job using kwargs
        job_id = add_cron_job(
            execute_recurring_task,
            second='*/5',  # Every 5 seconds
            args=["Check gym availability"]
        )
        logger.info(f"Created cron job: {job_id}")

        # List all jobs
        jobs = list_jobs()
        logger.info(f"Active jobs: {len(jobs)}")
        for job in jobs:
            logger.info(f"  - {job.id}: next run at {job.next_run_time}")

        # Wait for tasks to execute
        logger.info("Waiting for tasks to execute...")
        await asyncio.sleep(15)

        # Remove the job
        remove_job(job_id)

    finally:
        shutdown_scheduler()


if __name__ == '__main__':
    asyncio.run(main())
