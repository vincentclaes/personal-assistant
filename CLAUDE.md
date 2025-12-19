# CLAUDE.md - Development Guide for Personal Assistant

This guide helps AI assistants (like Claude) work effectively on this personal assistant project.

## Project Overview

A Python-based personal assistant with:
- **Gym booking automation** (`book_gym.py`) - Browser automation using browser-use to book gym sessions with user confirmation
- **Telegram bot** (`interact_with_telegram.py`) - Simple bot that responds to messages

**Tech stack:**
- Python 3.12+
- `uv` for dependency management
- `browser-use` for web automation
- `python-telegram-bot` for Telegram integration
- Environment variables for credentials (`.env` file)

## Development Guidelines

### Dependency Management
- **Always use `uv` exclusively** - Never use `pip` or `venv` directly
- Add dependencies: `uv add <package>`
- Run scripts: `uv run python <script>.py`
- Sync dependencies: `uv sync`

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
# 1. Write test in test_feature.py
# 2. Run test to see it fail
uv run python -m pytest test_feature.py

# 3. Implement feature
# 4. Run test again to see it pass
uv run python -m pytest test_feature.py
```

### Browser Automation (browser-use)

**Key documentation:** [browser-use AGENTS.md](https://github.com/browser-use/browser-use/blob/main/AGENTS.md)

**Important patterns:**
- Use `headless=False` for debugging - always see what the browser is doing
- Create custom `Controller` with `@controller.registry.action()` for user interaction
- The `ask_user` tool pattern is critical - use it before any booking/purchase actions
- Pass `sensitive_data` dict to Agent for credentials (never hardcode)
- Enable `use_vision=True` for better page understanding

**Example user confirmation pattern:**
```python
@controller.registry.action('Ask the user a question and wait for response')
def ask_user(question: str) -> ActionResult:
    user_response = input("Your response: ").strip()
    return ActionResult(extracted_content=user_response)
```

### Telegram Bot (python-telegram-bot)

**Key documentation:** [Your First Bot Tutorial](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Extensions---Your-first-Bot)

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
- `OPENAI_API_KEY` - For browser-use LLM (if using OpenAI)

**Keep this pattern:**
- Store secrets in `.env` (never commit this file)
- Load with `python-dotenv`
- Access with `os.getenv()`
- No additional validation or config layers needed

### Project Structure

**Monolithic approach:** Keep related functionality together
- Each major feature can be its own script
- Don't split into many small utility modules
- Duplicate simple code rather than creating premature abstractions
- Only refactor when complexity becomes a real problem

---

## Quick Reference

- **Run script:** `uv run python script.py`
- **Add dependency:** `uv add package-name`
- **Run tests:** `uv run python -m pytest`
- **TDD cycle:** Write test → Watch fail → Implement → Watch pass
- **One test rule:** One happy path test per feature, no more
