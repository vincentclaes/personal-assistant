"""
PTB SQLite JobStore adapter for python-telegram-bot v22+

This module provides a custom jobstore that makes telegram.ext.Job instances
serializable for SQLite storage with APScheduler, inspired by ptbcontrib.

Note: SQLite has multi-threading limitations, but works for simple bot use cases.
"""

from apscheduler.job import Job as APSJob
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from telegram.ext import Application
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


def configure_ptb_jobstore(application: Application, db_path: str) -> None:
    """
    Configure PTB-compatible jobstore for the application.

    This function sets up SQLite-based job persistence for telegram jobs.

    Args:
        application: The Telegram Application instance
        db_path: Path to the SQLite database file

    Example:
        configure_ptb_jobstore(application, "bot_data.db")
    """
    if not application.job_queue:
        raise RuntimeError("Application must have job_queue enabled")

    # Create PTB-aware jobstore
    jobstore = PTBSQLiteJobStore(
        application=application,
        url=f'sqlite:///{db_path}'
    )

    # Configure scheduler with our jobstore
    # Must use scheduler.configure() to properly set jobstores
    scheduler = application.job_queue.scheduler
    scheduler.configure(jobstores={'default': jobstore})

    print(f"✅ PTB JobStore configured with SQLite ({db_path})")
