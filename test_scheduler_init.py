import pytest
from app import create_scheduler

def test_create_scheduler():
    """Test scheduler initialization."""
    scheduler = create_scheduler()

    # Verify scheduler is created and not started yet
    assert scheduler is not None
    assert not scheduler.running

    # Clean up
    if scheduler.running:
        scheduler.shutdown(wait=False)
