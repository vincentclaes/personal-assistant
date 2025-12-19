"""Task execution handlers for scheduled jobs."""
from typing import Callable
from telegram import Bot
from loguru import logger
from task_store import TaskStore


def send_reminder_handler(bot: Bot, task_store: TaskStore) -> Callable:
    """Create reminder handler function.

    Args:
        bot: Telegram Bot instance
        task_store: TaskStore instance

    Returns:
        Async handler function for reminder execution
    """
    async def handler(job_id: str) -> None:
        """Execute reminder task.

        Args:
            job_id: APScheduler job ID
        """
        logger.info(f"Executing reminder: {job_id}")

        try:
            # Load task metadata
            metadata = task_store.get_task(job_id)

            if not metadata:
                logger.error(f"No metadata found for job {job_id}")
                return

            chat_id = metadata.get("chat_id")
            message = metadata.get("preferences", {}).get("message", "Reminder!")

            # Send reminder message
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔔 Reminder: {message}"
            )

            logger.info(f"Reminder sent to chat {chat_id}")

        except Exception as e:
            logger.error(f"Error sending reminder {job_id}: {e}")

    return handler


def gym_booking_handler(bot: Bot, task_store: TaskStore) -> Callable:
    """Create gym booking handler function.

    Args:
        bot: Telegram Bot instance
        task_store: TaskStore instance

    Returns:
        Async handler function for gym booking execution
    """
    async def handler(job_id: str) -> None:
        """Execute gym booking task.

        Args:
            job_id: APScheduler job ID
        """
        logger.info(f"Executing gym booking: {job_id}")

        try:
            # Load task metadata
            metadata = task_store.get_task(job_id)

            if not metadata:
                logger.error(f"No metadata found for job {job_id}")
                return

            chat_id = metadata.get("chat_id")
            preferences = metadata.get("preferences", {})

            # TODO: Check available slots and send to user
            # For now, just send a placeholder message
            await bot.send_message(
                chat_id=chat_id,
                text="⏰ Time to book your gym session! (Feature in progress)"
            )

            logger.info(f"Gym booking notification sent to chat {chat_id}")

        except Exception as e:
            logger.error(f"Error executing gym booking {job_id}: {e}")

    return handler
