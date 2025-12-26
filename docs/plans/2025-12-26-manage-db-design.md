# Database Management CLI Design

**Date:** 2025-12-26
**Goal:** Refactor `export_db_to_json.py` into `manage_db.py` with Typer CLI supporting export and clear operations.

## Commands

### Export Command
```bash
manage_db.py export [--output PATH]
```
- Exports all database data to JSON
- Default output: `app.db.json`
- Shows count of exported entries

### Clear Command
```bash
manage_db.py clear --user-id USER_ID [--full]
```
- Clears data for specific user
- `--user-id`: Required Telegram user ID (integer)
- `--full`: Optional flag
  - Without: Clears only chat history, keeps user info
  - With: Deletes entire user entry

## Implementation

**Minimal approach:**
- Single file with two Typer commands
- Reuse existing export logic
- Use same SqliteDict pattern as app.py
- Fail loudly with clear error messages
- No try-except blocks unless necessary

**Database structure:**
```python
{
  user_id: {
    "user": {...},           # User info from Telegram
    "chat_history": [...]    # List of messages
  }
}
```

## Safety
- Clear requires explicit `--user-id` (no clear-all)
- Error if user not found
- Print what was deleted
