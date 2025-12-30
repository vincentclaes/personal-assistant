#!/usr/bin/env python
# pylint: disable=unused-argument
"""
Timer Bot with SQLite persistence.

This Bot uses the Application class to handle the bot and the JobQueue with
SQLite persistence to send timed messages that survive restarts.

Usage:
Basic Alarm Bot example, sends a message after a set time.
Jobs are persisted to timerbot.db and will survive application restarts.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
import os
from typing import Any

from apscheduler.job import Job as APSJob
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext._jobqueue import Job

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class PTBSQLiteJobStore(SQLAlchemyJobStore):
    """SQLite jobstore that makes telegram.ext.Job class storable."""

    def __init__(self, application: Application, url: str = "sqlite:///timerbot.db") -> None:
        """Initialize with Application instance and SQLite database path.

        Args:
            application: Application instance for CallbackContext recreation
            url: SQLite database URL (default: sqlite:///timerbot.db)
        """
        self.application = application
        super().__init__(url=url)
        logger.info(f"Initialized SQLite jobstore with database: {url}")

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    await update.message.reply_text("Hi! Use /set <seconds> to set a timer")


async def alarm(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"Beep! {job.data} seconds are over!")


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id
    try:
        # args[0] should contain the time for the timer in seconds
        due = float(context.args[0])
        if due < 0:
            await update.effective_message.reply_text("Sorry we can not go back to future!")
            return

        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(alarm, due, chat_id=chat_id, name=str(chat_id), data=due)

        text = "Timer successfully set!"
        if job_removed:
            text += " Old one was removed."
        await update.effective_message.reply_text(text)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Usage: /set <seconds>")


async def unset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Timer successfully cancelled!" if job_removed else "You have no active timer."
    await update.message.reply_text(text)


def main() -> None:
    """Run bot."""
    # Get token from environment
    token = os.getenv('TELEGRAM_API_KEY')
    if not token:
        raise ValueError("TELEGRAM_API_KEY not found in environment variables")

    # Create the Application and pass it your bot's token
    application = Application.builder().token(token).build()

    # Create SQLite jobstore with the application instance
    jobstore = PTBSQLiteJobStore(application=application, url="sqlite:///timerbot.db")

    # Configure the job queue to use our SQLite jobstore
    job_queue = application.job_queue
    job_queue.scheduler.add_jobstore(jobstore, alias="default")

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler("set", set_timer))
    application.add_handler(CommandHandler("unset", unset))

    logger.info("Starting timer bot with SQLite persistence...")

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
