# Personal Assistant Scheduler Design

**Date:** 2025-12-19
**Status:** Approved

## Overview

Design for adding scheduling capabilities to the personal assistant, enabling users to create recurring tasks (gym bookings) and one-time reminders through natural language via Telegram.

## Architecture

### Core Components

**Telegram Bot (Hub)**

- Central interface running continuously
- Handles all user interactions
- Hosts APScheduler instance
- Manages conversation flow with Pydantic AI agent

**Pydantic AI Agent (Brain)**

- Interprets natural language requests
- Extracts intent and task parameters
- Asks clarifying questions when details are unclear
- Always confirms before creating schedules
- Calls tools to execute actions

**APScheduler with SQLite (Memory)**

- Runs inside Telegram bot process
- Stores scheduled jobs in SQLite database (schedules.db)
- Survives process restarts
- Triggers task execution at scheduled times

**sqlitedict (Context Store)**

- Stores task metadata and user preferences
- Separate from APScheduler's job storage
- Provides rich context when tasks execute

### Execution Flow Example

1. User: "Book my gym session every Monday at 7am"
2. Agent asks: "Which weeks? Every week or specific dates?"
3. User: "Every week"
4. Agent confirms: "Schedule gym booking every Monday at 7am?"
5. User: "Yes"
6. APScheduler stores recurring job, sqlitedict stores user preferences
7. Every Monday at 7am:
   - Scheduler triggers execution
   - Bot checks available gym slots
   - Sends Telegram message with options
   - User selects time slot
   - Booking executes with confirmation

## Data Storage Strategy

### APScheduler SQLite Store (schedules.db)

Handles scheduling mechanics:

- Job ID and trigger configuration (cron, interval, one-time)
- Next run time and execution history
- Job function reference and parameters

### sqlitedict Store (task_metadata.db)

Handles task context:

- User's original natural language request
- Clarification conversation history
- Task-specific preferences
- User ID (Telegram chat ID)
- Task type ('gym_booking' or 'reminder')
- Creation timestamp

### Data Model Example

```python
# sqlitedict entry (key = APScheduler job_id)
{
  "job_id_123": {
    "task_type": "gym_booking",
    "user_id": 12345,
    "chat_id": 67890,
    "original_request": "book gym every Monday at 7am",
    "preferences": {
      "preferred_hours": ["07:00", "08:00"],
      "max_per_week": 2
    },
    "created_at": "2025-12-19T10:30:00"
  }
}
```

### Data Flow

When APScheduler triggers a job:

1. Job handler receives job_id
2. Looks up metadata in sqlitedict using job_id
3. Gets user's Telegram chat_id and task preferences
4. Executes task logic with user context
5. Sends results to user via Telegram

## Pydantic AI Agent & Tools

### Agent Tools

**1. create_schedule**

- Parameters: task_type, schedule_pattern, task_params
- Creates job in APScheduler
- Stores metadata in sqlitedict
- Returns confirmation message

**2. list_schedules**

- Returns all active schedules for requesting user
- Formats human-friendly descriptions

**3. cancel_schedule**

- Parameters: job_id or natural language reference
- Removes from APScheduler and sqlitedict
- Confirms cancellation

**4. execute_gym_booking**

- Called by scheduler at trigger time
- Loads user preferences from sqlitedict
- Runs browser automation to check slots
- Sends options via Telegram InlineKeyboard
- Waits for user selection
- Executes booking

**5. send_reminder**

- Called by scheduler at trigger time
- Loads reminder message from sqlitedict
- Sends Telegram message to user

### Agent Conversation Pattern

**Example: Creating a Reminder**

```
User: "Remind me to call dentist tomorrow at 2pm"

Agent extracts: task_type=reminder, time=tomorrow 2pm, message="call dentist"

Agent: "Should I remind you just once, or repeat this?"

User: "Just once"

Agent: "I'll send you a reminder tomorrow at 2pm to call dentist. Confirm?"

User: "Yes"

Agent calls create_schedule tool

Agent: "✓ Reminder set for tomorrow at 2pm"
```

**Example: Creating Recurring Gym Booking**

```
User: "Book gym every Monday at 7am"

Agent: "Which weeks should I book? Every week or specific dates?"

User: "Every week"

Agent: "What should I do if 7am isn't available?"

User: "Try 8am, otherwise skip"

Agent: "I'll book gym every Monday at 7am (fallback 8am). Confirm?"

User: "Yes"

Agent calls create_schedule tool with preferences

Agent: "✓ Scheduled gym booking every Monday at 7am"
```

## Task Execution Flow

### Gym Booking Execution

1. APScheduler calls `execute_gym_booking(job_id)` at scheduled time
2. Load metadata from sqlitedict (user chat_id, preferences)
3. Run browser automation to check available gym slots
4. Send Telegram message with InlineKeyboard buttons:
   ```
   Available gym slots:
   [7am] [8am] [12pm]
   [Skip Today]
   ```
5. User clicks button
6. Bot receives CallbackQuery
7. Execute booking with selected time
8. Send confirmation: "✓ Booked gym session at 7am"

### Reminder Execution

1. APScheduler calls `send_reminder(job_id)` at scheduled time
2. Load metadata from sqlitedict (chat_id, message)
3. Send Telegram message: "🔔 Reminder: call dentist"
4. Done

### Error Handling

**Gym booking failures:**

- Website down, no slots available, browser crashes
- Send Telegram message: "⚠️ Couldn't book gym - no available slots. Try again?"
- Provide [Retry] [Skip] buttons
- Log error, don't crash scheduler

**Reminder failures:**

- Log error
- Retry once after 5 minutes
- If still fails, notify user of delivery failure

**General principles:**

- Never crash the scheduler
- Always notify user of failures
- Log all errors for debugging
- Fail loudly with clear messages

### Telegram Integration

**Replace terminal input with buttons:**

- Use `InlineKeyboardMarkup` for options
- Handle `CallbackQueryHandler` for button clicks
- Encode action context in callback_data

**State management for pending actions:**

- Store in memory dict: `{callback_id: action_context}`
- Short-lived (5 min timeout)
- Lost on restart is acceptable (user can retry)

## Technical Implementation

### File Structure

```
personal-assistant/
├── interact_with_telegram.py  # Main bot with scheduler integration
├── book_gym.py                 # Gym booking logic (modified for Telegram)
├── task_store.py              # sqlitedict wrapper for task metadata
├── schedules.db               # APScheduler SQLite store
├── task_metadata.db           # sqlitedict store
├── .env                       # Environment variables
└── tests/
    ├── test_schedule_creation.py
    ├── test_gym_booking.py
    └── test_reminders.py
```

### Dependencies

```bash
uv add apscheduler sqlitedict pydantic-ai
```

### APScheduler Setup

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore

scheduler = AsyncIOScheduler(
    datastore=SQLAlchemyDataStore(url="sqlite:///schedules.db")
)
scheduler.start()
```

Uses AsyncIOScheduler because python-telegram-bot is async.

### Pydantic AI Integration

Agent runs inside Telegram message handlers:

1. User sends message to bot
2. Handler passes message to Pydantic AI agent with tools
3. Agent interprets intent and calls appropriate tools
4. Tools interact with APScheduler and sqlitedict
5. Agent formats response
6. Bot sends response via Telegram

### Browser Automation Adaptation

Current `book_gym.py` uses terminal `input()` via Controller action.

**For scheduled execution:**

- Remove `ask_user` Controller action
- Make `book_gym.py` return available slots as data
- Telegram bot formats slots as InlineKeyboard
- User selects via button click
- Booking proceeds with selected slot

**For manual execution (user runs script directly):**

- Keep terminal-based flow as fallback/testing mode
- Detect if running in bot context vs standalone

### Timezone Handling

Configure APScheduler with user's timezone:

- Set timezone when creating jobs
- Store timezone in environment variable
- "7am" means 7am local time, not UTC

```python
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

trigger = CronTrigger(
    day_of_week='mon',
    hour=7,
    timezone=ZoneInfo(os.getenv('TIMEZONE', 'Europe/Brussels'))
)
```

## Testing Strategy

Follow TDD with one happy path test per feature.

### Test 1: Schedule Creation

```python
def test_create_reminder_schedule():
    """Test creating a one-time reminder through agent."""
    # User sends message
    # Agent extracts details and confirms
    # Verify job exists in APScheduler
    # Verify metadata in sqlitedict
    # Verify confirmation message sent
```

### Test 2: Gym Booking Execution

```python
def test_gym_booking_execution():
    """Test scheduled gym booking execution."""
    # Create a scheduled gym booking job
    # Manually trigger the job
    # Mock browser automation to return fake slots
    # Verify Telegram message sent with slot options
    # Simulate user button click
    # Verify booking executed with selected slot
```

### Test 3: Reminder Execution

```python
def test_reminder_execution():
    """Test scheduled reminder delivery."""
    # Create a scheduled reminder job
    # Manually trigger the job
    # Verify correct Telegram message sent to correct user
```

### Mocking Strategy

**Mock:**

- Telegram API calls (use python-telegram-bot test utilities)
- Browser automation (mock book_gym to return fake data)
- Time (use APScheduler test helpers for time simulation)

**Don't mock:**

- APScheduler (use real instance with test database)
- sqlitedict (use real instance with temp file)

**Test database cleanup:**

- Create fresh test databases before each test
- Clean up after each test
- Use pytest fixtures for setup/teardown

## Deployment

### AWS Deployment Options

**Recommended: EC2 with systemd**

- Run bot as systemd service
- SQLite files on EBS volume
- Simple, reliable, always running
- Use t4g.micro (ARM) for cost efficiency

**Alternative 1: ECS Fargate**

- Dockerize bot
- Mount EFS for persistent SQLite files
- Auto-restart on crashes
- More complex but more "cloud-native"

**Alternative 2: Lightsail Container**

- Simpler than ECS
- Cheaper for small workloads
- Still need persistent storage solution

### Recommended Setup: EC2 + systemd

**Storage:**

- SQLite files in `/var/lib/telegram-bot/`
- Regular backups to S3 (daily cron job)
- EBS volume with snapshots enabled

**Systemd service:**

```ini
[Unit]
Description=Personal Assistant Telegram Bot
After=network.target

[Service]
Type=simple
User=telegram-bot
WorkingDirectory=/opt/telegram-bot
Environment="DB_PATH=/var/lib/telegram-bot"
ExecStart=/opt/telegram-bot/.venv/bin/uv run python interact_with_telegram.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Environment Variables

Add to `.env`:

```
TELEGRAM_API_KEY=<token>
QORE_PASSWORD=<password>
OPENAI_API_KEY=<key>
PYDANTIC_AI_MODEL=openai:gpt-4
TIMEZONE=Europe/Brussels
DB_PATH=/var/lib/telegram-bot
```

### Monitoring

**Logging with loguru:**

- Log scheduled task creation/cancellation
- Log task executions (success/failure)
- Log agent tool calls
- Log all errors with stack traces

**CloudWatch Logs:**

- Configure CloudWatch Logs agent on EC2
- Ship logs to CloudWatch for debugging
- Set up alarms for error rates

**Health checks:**

- Simple HTTP endpoint that returns 200 if scheduler is running
- CloudWatch alarm if endpoint fails

## Task Types Supported

### Initial Implementation

**1. Gym Bookings**

- Recurring (weekly pattern)
- User preferences for time slots
- Interactive confirmation before booking
- Fallback time slots if preferred unavailable

**2. Reminders**

- One-time or recurring
- Simple text message delivery
- No user interaction required at execution time

### Future Extensions

Design is extensible for additional task types:

- Bill payment reminders with due dates
- Medication reminders
- Calendar event creation
- Email/SMS notifications
- Custom webhook calls

## Success Criteria

**User Experience:**

- User creates schedules with natural language
- Agent asks clarifying questions when needed
- Always confirms before creating schedule
- Clear feedback when tasks execute
- Easy to list and cancel schedules

**Reliability:**

- Schedules survive bot restarts
- Errors don't crash scheduler
- User always notified of execution status
- Graceful degradation on failures

**Maintainability:**

- Simple monolithic structure
- Clear separation of concerns
- Easy to add new task types
- Straightforward testing

## Migration Path

Since this is a new feature, no migration needed. However:

**Existing book_gym.py:**

- Keep standalone functionality
- Add bot integration mode
- Preserve terminal-based testing capability

**Existing telegram bot:**

- Extend with scheduler and agent
- Preserve existing simple message handling
- Gradual rollout of scheduling features

## Open Questions & Future Considerations

**Not in initial scope:**

- Web dashboard for schedule management
- Multi-user support (assume single user initially)
- Advanced scheduling (business days, holidays)
- Task dependencies (do X after Y completes)
- Notification preferences (Telegram vs email vs SMS)

These can be added later if needed.
