#!/usr/bin/env python3
"""Test manage_db.py database management CLI."""

import tempfile
import json
from pathlib import Path
from sqlitedict import SqliteDict
from typer.testing import CliRunner
from personal_assistant.cli import app


def test_db_export_command():
    """Test exporting database to JSON file."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test database with sample data
        db_path = Path(tmpdir) / "test.db"
        output_path = Path(tmpdir) / "output.json"

        with SqliteDict(str(db_path), autocommit=True) as db:
            db[12345] = {
                "user": {"id": 12345, "first_name": "Vincent"},
                "chat_history": [{"role": "user", "content": "Hello"}],
            }
            db[67890] = {
                "user": {"id": 67890, "first_name": "Alice"},
                "chat_history": [],
            }

        # Run export command with custom paths
        result = runner.invoke(
            app,
            ["db", "export", "--output", str(output_path), "--db-path", str(db_path)],
        )

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed: {result.stdout}"
        assert "2 entries" in result.stdout

        # Verify JSON file was created with correct data
        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)

        assert len(data) == 2
        assert "12345" in data
        assert data["12345"]["user"]["first_name"] == "Vincent"


def test_clear_chat_history_only():
    """Test clearing only chat history for a user (default behavior)."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create test database with user data
        with SqliteDict(str(db_path), autocommit=True) as db:
            db[12345] = {
                "user": {"id": 12345, "first_name": "Vincent"},
                "chat_history": [{"role": "user", "content": "Hello"}],
            }

        # Run clear command without --full flag
        result = runner.invoke(
            app, ["db", "clear", "--user-id", "12345", "--db-path", str(db_path)]
        )

        # Verify command succeeded
        assert result.exit_code == 0
        assert "chat history" in result.stdout.lower()

        # Verify only chat history was cleared
        with SqliteDict(str(db_path), autocommit=False) as db:
            user_data = db[12345]
            assert user_data["user"]["first_name"] == "Vincent"
            assert user_data["chat_history"] == []


def test_db_clear_full_user_entry():
    """Test deleting entire user entry with --full flag."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create test database with user data
        with SqliteDict(str(db_path), autocommit=True) as db:
            db[12345] = {
                "user": {"id": 12345, "first_name": "Vincent"},
                "chat_history": [{"role": "user", "content": "Hello"}],
            }

        # Run clear command with --full flag
        result = runner.invoke(
            app,
            ["db", "clear", "--user-id", "12345", "--full", "--db-path", str(db_path)],
        )

        # Verify command succeeded
        assert result.exit_code == 0
        assert "entire entry" in result.stdout.lower()

        # Verify user was completely deleted
        with SqliteDict(str(db_path), autocommit=False) as db:
            assert 12345 not in db


def test_db_clear_nonexistent_user():
    """Test clearing data for user that doesn't exist."""
    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"

        # Create empty database
        with SqliteDict(str(db_path), autocommit=True):
            pass

        # Run clear command for non-existent user
        result = runner.invoke(
            app, ["db", "clear", "--user-id", "99999", "--db-path", str(db_path)]
        )

        # Verify command reports user not found
        assert result.exit_code != 0
        assert "not found" in result.stdout.lower()


if __name__ == "__main__":
    test_export_command()
    test_clear_chat_history_only()
    test_clear_full_user_entry()
    test_clear_nonexistent_user()
    print("✅ All tests passed!")
