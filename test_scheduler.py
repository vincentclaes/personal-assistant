"""
Tests for scheduler module with per-user job management.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import database
import scheduler
from scheduler import (
    add_user_job,
    get_user_jobs,
    remove_user_job,
    shutdown_scheduler,
)


def sample_task(message: str) -> None:
    """Sample task for testing."""
    pass


@pytest.fixture(autouse=True)
def test_database():
    """Use a temporary database for tests."""
    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "test_scheduler.db"

        # Patch the DB_PATH in database module so scheduler picks it up
        with patch.object(database, 'DB_PATH', str(test_db_path)):
            # Reset the singleton scheduler to force recreation with test DB
            scheduler._scheduler = None

            yield

            # Clean up: shutdown scheduler and reset singleton
            shutdown_scheduler()
            scheduler._scheduler = None


def test_add_user_job_creates_namespaced_job_id():
    """Test that adding a user job creates a job with user ID namespace and unique identifier."""
    user_id = 123
    job_type = "morning_reminder"
    unique_id = "weekday_9am"

    job_id = add_user_job(
        user_id=user_id,
        job_type=job_type,
        unique_id=unique_id,
        func=sample_task,
        hour=9,
        minute=0,
        args=["Good morning!"]
    )

    # Job ID should be in format: user_{user_id}_{job_type}_{unique_id}
    expected_job_id = f"user_{user_id}_{job_type}_{unique_id}"
    assert job_id == expected_job_id


def test_add_multiple_jobs_for_same_user_and_type():
    """Test that a user can have multiple jobs of the same type with different unique IDs."""
    user_id = 123
    job_type = "reminder"

    job_id_1 = add_user_job(
        user_id=user_id,
        job_type=job_type,
        unique_id="morning",
        func=sample_task,
        hour=9,
        minute=0,
        args=["Morning reminder"]
    )

    job_id_2 = add_user_job(
        user_id=user_id,
        job_type=job_type,
        unique_id="evening",
        func=sample_task,
        hour=18,
        minute=0,
        args=["Evening reminder"]
    )

    assert job_id_1 == f"user_{user_id}_{job_type}_morning"
    assert job_id_2 == f"user_{user_id}_{job_type}_evening"
    assert job_id_1 != job_id_2


def test_get_user_jobs_returns_only_user_jobs():
    """Test that get_user_jobs returns only jobs for the specified user."""
    user_123 = 123
    user_456 = 456

    # Add jobs for user 123
    add_user_job(
        user_id=user_123,
        job_type="reminder",
        unique_id="morning",
        func=sample_task,
        hour=9,
        args=["User 123 morning"]
    )

    # Add jobs for user 456
    add_user_job(
        user_id=user_456,
        job_type="reminder",
        unique_id="evening",
        func=sample_task,
        hour=18,
        args=["User 456 evening"]
    )

    # Get jobs for user 123
    user_123_jobs = get_user_jobs(user_123)

    # Should only have 1 job for user 123
    assert len(user_123_jobs) == 1
    assert user_123_jobs[0].id.startswith(f"user_{user_123}_")


def test_remove_user_job_removes_specific_job():
    """Test that remove_user_job removes the correct job."""
    user_id = 789
    job_type = "reminder"
    unique_id = "test"

    # Add a job
    job_id = add_user_job(
        user_id=user_id,
        job_type=job_type,
        unique_id=unique_id,
        func=sample_task,
        hour=10,
        args=["Test reminder"]
    )

    # Verify job exists
    user_jobs = get_user_jobs(user_id)
    assert len(user_jobs) == 1

    # Remove the job
    result = remove_user_job(user_id, job_type, unique_id)

    # Verify job was removed
    assert result is True
    user_jobs_after = get_user_jobs(user_id)
    assert len(user_jobs_after) == 0
