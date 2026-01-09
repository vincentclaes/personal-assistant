# CLAUDE.md - Development Guide for Personal Assistant

This guide helps AI assistants (like Claude) work effectively on this personal assistant project.

## Project Overview

A Python-based personal assistant with Telegram bot integration and automated scheduling capabilities.

**Project Structure:**

- `personal_assistant/` - Main source code package
  - `app.py` - Telegram bot application with PydanticAI agent
  - `database.py` - Database configuration and constants
  - `manage_db.py` - CLI tool for database management
- `tests/` - Test suite with pytest
  - Import modules using: `from personal_assistant.app import ...`

**Tech stack:**

- Python 3.12+
- `uv` for dependency management
- `pydantic-ai` for AI agent capabilities
- `python-telegram-bot` for Telegram integration
- `sqlitedict` for user data persistence
- `APScheduler` for scheduled tasks
- Environment variables for credentials (`.env` file)

## Development Guidelines

### Dependency Management

- **Always use `uv` exclusively** - Never use `pip` or `venv` directly
- Add dependencies: `uv add <package>`
- Run the app: `uv run python -m personal_assistant.app`
- Run tests: `uv run python -m pytest`
- Sync dependencies: `uv sync`

### Module Imports

- Source code is in the `personal_assistant/` package
- Tests are in the `tests/` directory
- Import modules using: `from personal_assistant.app import function_name`
- When running modules: `python -m personal_assistant.app`

### Code Style

- Follow **PEP 8** conventions
- Use **type hints** for function parameters and return values
- Write **clear docstrings** for all functions
- Keep code readable and straightforward

### Testing Approach

- **Test-Driven Development (TDD)** - Write the test first, then implement
- **One happy path test** per feature - Don't add more unless explicitly requested
- Tests should verify the feature works as expected in the normal case
- Let tests guide the implementation

## AI Agent Instructions

### Core Principles

**Simplicity First**

- Prefer straightforward scripts over abstractions
- Don't create utilities, helpers, or shared modules prematurely
- Only add complexity when there's a clear, present need
- Keep related functionality together in monolithic files rather than splitting into many small modules

**Fail Loudly**

- Let errors propagate with clear error messages
- Don't hide failures with try-except blocks unless absolutely necessary
- Clear error messages are better than graceful degradation
- Makes debugging automation much easier

**Safety with User Actions**

- Never auto-book, auto-send, or auto-commit the user to anything without confirmation
- Always use interactive prompts (`ask_user` tool, input(), etc.) for actions that:
  - Cost money
  - Send messages to others
  - Make reservations or bookings
  - Modify external systems

### Test-Driven Development Workflow

**Always follow RED-GREEN-REFACTOR:**

1. **RED** - Write the test first, run it, watch it fail
2. **GREEN** - Write minimal code to make the test pass
3. **REFACTOR** - Clean up if needed (but keep it simple!)

**Testing rules:**

- Write exactly **one happy path test** per feature
- Don't add edge case tests, error tests, or multiple scenarios unless explicitly requested
- Test should verify the normal, expected behavior works
- Run the test before implementing to ensure it actually fails

**Example workflow:**

```bash
# 1. Write test in tests/test_feature.py
# 2. Run test to see it fail
uv run python -m pytest tests/test_feature.py

# 3. Implement feature in personal_assistant/
# 4. Run test again to see it pass
uv run python -m pytest tests/test_feature.py
```

### PydanticAI Agent

**Current implementation:**

- Main agent is in `personal_assistant/app.py`
- Uses AWS Bedrock Claude Sonnet 4.5 via `pydantic-ai`
  - Model: `bedrock:eu.anthropic.claude-sonnet-4-5-20250929-v1:0`
- Chat history persisted per user with `sqlitedict`
- System prompts updated dynamically

### Telegram Bot (python-telegram-bot)

**Key documentation:** [Your First Bot Tutorial](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions---Your-first-Bot)

**Current implementation:**

- Bot handles text messages and commands
- Integrates with PydanticAI agent for responses
- Scheduled jobs using APScheduler

**Important patterns:**

- Use `Application.builder().token(TOKEN).build()` for setup
- Register handlers with `add_handler()`
- `CommandHandler` for `/commands`, `MessageHandler` for text messages
- Always use `async/await` for handler functions
- Load token from environment: `os.getenv('TELEGRAM_API_KEY')`

### Environment Variables & Credentials

**Current approach:** Use `.env` files with `os.getenv()`

**Pattern:**

```python
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TELEGRAM_API_KEY')
```

**Required environment variables:**

- `TELEGRAM_API_KEY` - Telegram bot token
- `QORE_PASSWORD` - Gym booking system password
- `AWS_ACCESS_KEY_ID` - AWS credentials for Bedrock (both orchestrator and browser agents)
- `AWS_SECRET_ACCESS_KEY` - AWS credentials for Bedrock
- `AWS_REGION` - AWS region for Bedrock (e.g., eu-west-1)

**Note:** `OPENAI_API_KEY` is no longer required - both agents now use AWS Bedrock Claude Sonnet 4.5

**Keep this pattern:**

- Store secrets in `.env` (never commit this file)
- Load with `python-dotenv`
- Access with `os.getenv()`
- No additional validation or config layers needed

### Project Structure

**Package-based organization:**

- Source code in `personal_assistant/` package
- Tests in `tests/` directory
- Keep related functionality together in modules
- Avoid premature abstractions
- Only refactor when complexity becomes a real problem

### Docker Deployment

**Dockerfile:**

- Copies `personal_assistant/` directory into container
- Runs with: `CMD ["python", "-m", "personal_assistant.app"]`
- Uses writable `/tmp` directory for database and cache

**Environment variables** (set in Terraform):

- `TELEGRAM_API_KEY`, `QORE_PASSWORD`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` - For Bedrock (both agents)
- `DB_PATH=/tmp/app.db` for writable storage in ECS Fargate
- `HOME`, `XDG_*` dirs all set to `/tmp`

---

## Quick Reference

- **Run app:** `uv run python -m personal_assistant.app`
- **Run tests:** `uv run python -m pytest`
- **Run specific test:** `uv run python -m pytest tests/test_database.py`
- **Add dependency:** `uv add package-name`
- **Manage DB:** `uv run python -m personal_assistant.manage_db --help`
- **TDD cycle:** Write test → Watch fail → Implement → Watch pass
- **One test rule:** One happy path test per feature, no more
