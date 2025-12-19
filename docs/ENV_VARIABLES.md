# Environment Variables

Required environment variables for the personal assistant bot.

## Telegram Configuration

- `TELEGRAM_API_KEY` - Bot token from @BotFather
- Required for: Telegram bot API access

## Gym Booking

- `QORE_PASSWORD` - Password for gym booking website
- Required for: Automated gym session booking

## AI/LLM Configuration

- `OPENAI_API_KEY` - OpenAI API key
- Required for: Browser automation (browser-use) and Pydantic AI agent

## Scheduling

- `TIMEZONE` - Timezone for scheduling (default: "Europe/Brussels")
- Optional, defaults to Europe/Brussels if not set
- Format: IANA timezone string (e.g., "America/New_York", "Asia/Tokyo")

## Database Paths

- `DB_PATH` - Directory for SQLite databases (default: current directory)
- Optional, defaults to "." if not set
- Scheduler database: `{DB_PATH}/schedules.db`
- Task metadata database: `{DB_PATH}/task_metadata.db`

## Example .env File

```
TELEGRAM_API_KEY=your_telegram_bot_token_here
QORE_PASSWORD=your_gym_password_here
OPENAI_API_KEY=your_openai_api_key_here
TIMEZONE=Europe/Brussels
DB_PATH=.
```
