# Personal Assistant Bot

A Python-based Telegram bot with AI-powered task scheduling capabilities.

## Features

- 🤖 **Natural Language Interface** - Talk to your bot naturally using Pydantic AI
- 🔔 **Smart Reminders** - One-time and recurring reminders
- 🏋️ **Gym Booking** - Automated gym session scheduling (in progress)
- 📅 **APScheduler Integration** - Persistent scheduling with SQLite
- 💾 **Task Metadata Storage** - Rich context storage with sqlitedict

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Telegram bot token from [@BotFather](https://t.me/botfather)
- OpenAI API key

### Installation

```bash
# Clone repository
git clone <repo-url>
cd personal-assistant

# Install dependencies
uv sync

# Create .env file
cp .env.example .env
# Edit .env with your credentials
```

### Environment Variables

See [docs/ENV_VARIABLES.md](docs/ENV_VARIABLES.md) for details.

Required:
- `TELEGRAM_API_KEY` - Your Telegram bot token
- `OPENAI_API_KEY` - OpenAI API key for Pydantic AI

Optional:
- `TIMEZONE` - Default: "Europe/Brussels"
- `DB_PATH` - Database directory, default: current directory

### Running the Bot

```bash
uv run python interact_with_telegram.py
```

You should see:
```
Starting bot with scheduler...
Task store initialized
Scheduler started
AI agent initialized
Bot is running! Send messages to @sidekick_pa_bot on Telegram.
```

## Usage

### Setting a Reminder

```
You: Remind me to call mom tomorrow at 2pm
Bot: I'll set a reminder for you tomorrow at 2pm to call mom. Should this be one-time or recurring?
You: One-time
Bot: ✓ Reminder set for 2025-12-20 14:00
```

### Listing Schedules

```
You: Show my schedules
Bot: Your scheduled tasks:
- reminder (one-time) [ID: abc123]
```

### Canceling a Schedule

```
You: Cancel reminder abc123
Bot: ✓ Schedule cancelled (ID: abc123)
```

## Project Structure

```
personal-assistant/
├── interact_with_telegram.py  # Main bot + scheduler + agent
├── task_store.py              # Task metadata (sqlitedict)
├── task_handlers.py           # Scheduled job executors
├── agent_tools.py             # Pydantic AI tools
├── gym_booking.py             # Gym automation module
├── book_gym.py                # Standalone gym booking
├── tests/                     # Test suite
├── docs/
│   ├── plans/                # Design documents
│   └── ENV_VARIABLES.md      # Environment variable docs
├── schedules.db              # APScheduler jobs (created at runtime)
├── task_metadata.db          # Task context (created at runtime)
└── .env                      # Your credentials (gitignored)
```

## Development

### Running Tests

```bash
# All tests
uv run python -m pytest

# Specific test file
uv run python -m pytest tests/test_task_store.py -v
```

### Development Guidelines

This project follows:
- **TDD** - Write tests first
- **YAGNI** - Keep it simple
- **Type hints** - For all functions
- **PEP 8** - Code style

See [CLAUDE.md](CLAUDE.md) for detailed guidelines.

## Contributing

1. Fork the repository
2. Create feature branch
3. Write tests first (TDD)
4. Implement feature
5. Open Pull Request

## License

MIT

---

Built with Python, Pydantic AI, APScheduler, and python-telegram-bot
