#!/usr/bin/env python3
"""CLI for personal assistant."""

import json

import typer
from sqlitedict import SqliteDict


app = typer.Typer()
db_app = typer.Typer()
app.add_typer(db_app, name="db", help="Database management commands")

DB_PATH = "app.db"
MY_USER_ID = 8249434738


@db_app.command()
def export(
    output: str = typer.Option("app.db.json", help="Output JSON file path"),
    db_path: str = typer.Option(DB_PATH, help="Database file path"),
) -> None:
    """Export all database data to JSON file."""
    data = {}
    with SqliteDict(db_path, autocommit=False) as db:
        for key in db.keys():
            data[str(key)] = db[key]

    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    typer.echo(f"✅ Exported {len(data)} entries from {db_path} to {output}")


@db_app.command()
def clear(
    user_id: int = typer.Option(MY_USER_ID, help="Telegram user ID to clear"),
    full: bool = typer.Option(
        False, help="Delete entire user entry (default: clear only chat history)"
    ),
    db_path: str = typer.Option(DB_PATH, help="Database file path"),
) -> None:
    """Clear data for a specific user."""
    with SqliteDict(db_path, autocommit=True) as db:
        if user_id not in db:
            typer.echo(f"❌ Error: User {user_id} not found in database")
            raise typer.Exit(code=1)

        if full:
            del db[user_id]
            typer.echo(f"✅ Deleted entire entry for user {user_id}")
        else:
            user_data = db[user_id]
            user_data["chat_history"] = []
            db[user_id] = user_data
            typer.echo(f"✅ Cleared chat history for user {user_id}")


if __name__ == "__main__":
    app()
