"""
Example of how to use the scheduler module from other Python modules.

This demonstrates importing and using the scheduler to add jobs.
"""

import asyncio
from datetime import datetime, timedelta

from loguru import logger

# Import scheduler functions
from scheduler import (
    add_cron_job,
    add_date_job,
    list_jobs,
    remove_job,
    shutdown_scheduler,
    start_scheduler,
)


async def my_task(message: str, user_id: int) -> None:
    """Example task that can be scheduled."""
    logger.info(f"📋 Task executed: {message} for user {user_id}")


async def send_reminder(reminder_text: str) -> None:
    """Example reminder task."""
    logger.info(f"⏰ Reminder: {reminder_text}")


async def main():
    """Example usage from another module."""
    # Start the scheduler
    start_scheduler()

    try:
        # Example 1: Add a cron job that runs every minute
        job1 = add_cron_job(
            my_task,
            minute='*',  # Every minute
            args=["Hourly check", 12345]
        )
        logger.info(f"Added recurring job: {job1}")

        # Example 2: Add a one-time job 10 seconds from now
        run_time = datetime.now() + timedelta(seconds=10)
        job2 = add_date_job(
            send_reminder,
            run_date=run_time,
            args=["Take a break!"]
        )
        logger.info(f"Added one-time reminder: {job2}")

        # Example 3: Add a cron job with a custom ID
        job3 = add_cron_job(
            my_task,
            job_id="gym_booking_check",
            day_of_week='mon,wed,fri',
            hour=7,
            minute=0,
            args=["Check gym slots", 12345]
        )
        logger.info(f"Added gym check job: {job3}")

        # List all jobs
        jobs = list_jobs()
        logger.info(f"\nAll scheduled jobs ({len(jobs)}):")
        for job in jobs:
            logger.info(f"  {job.id}: next run at {job.next_run_time}")

        # Wait for some tasks to execute
        logger.info("\nWaiting for tasks to execute...")
        await asyncio.sleep(1)

        # Clean up specific jobs
        logger.info("\nCleaning up...")
        remove_job(job1)
        remove_job(job2)
        remove_job(job3)

    finally:
        shutdown_scheduler()


if __name__ == '__main__':
    asyncio.run(main())
