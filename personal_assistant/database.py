"""
Database configuration constants for personal assistant.

Centralizes database paths used across multiple modules.
"""

import os
from pathlib import Path


# Database path used by all modules
# Use environment variable if set, otherwise use absolute path to app.db in project directory
_default_db_path = Path(__file__).parent.absolute() / "app.db"
DB_PATH = os.getenv("DB_PATH", str(_default_db_path))
