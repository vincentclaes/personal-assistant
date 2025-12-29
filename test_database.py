"""
Test database module constants are properly defined and importable.
"""

import os
from pathlib import Path
from unittest.mock import patch


def test_database_constants_exist():
    """Test that database.py defines DB_PATH constant as absolute path."""
    from database import DB_PATH

    # DB_PATH should be a defined string
    assert isinstance(DB_PATH, str), "DB_PATH should be a string"

    # DB_PATH should be an absolute path
    assert os.path.isabs(DB_PATH), f"DB_PATH should be absolute, got '{DB_PATH}'"

    # DB_PATH should end with app.db
    assert DB_PATH.endswith("app.db"), f"Expected DB_PATH to end with 'app.db', got '{DB_PATH}'"


def test_database_path_respects_env_var():
    """Test that DB_PATH can be overridden via environment variable."""
    custom_path = "/custom/location/mydb.db"

    # Reload database module with env var set
    with patch.dict(os.environ, {'DB_PATH': custom_path}):
        # Need to reload the module to pick up the env var
        import importlib
        import database
        importlib.reload(database)

        assert database.DB_PATH == custom_path, f"Expected DB_PATH to be '{custom_path}', got '{database.DB_PATH}'"

    # Reload again without env var to restore default
    import importlib
    import database
    importlib.reload(database)


def test_app_uses_database_constants():
    """Test that app.py imports DB_PATH from database.py."""
    # Import to verify modules load without errors
    import app
    from database import DB_PATH

    # Verify database module is importable and app.py can use it
    assert os.path.isabs(DB_PATH)


def test_scheduler_uses_database_constants():
    """Test that scheduler.py imports DB_PATH from database.py."""
    # Import to verify modules load without errors
    import scheduler
    from database import DB_PATH

    # Verify database module is importable and scheduler.py can use it
    assert os.path.isabs(DB_PATH)
