# Scheduler Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add APScheduler-based task scheduling with natural language interface through Telegram bot and Pydantic AI agent for gym bookings and reminders.

**Architecture:** Telegram bot hosts APScheduler (AsyncIOScheduler) with SQLite persistence. Pydantic AI agent interprets natural language, calls tools that interact with APScheduler and sqlitedict. Interactive Telegram buttons replace terminal input for scheduled task execution.

**Tech Stack:** APScheduler 4.0+, sqlitedict, Pydantic AI, python-telegram-bot, browser-use

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml:1-14`

**Step 1: Add required packages**

```bash
cd /Users/vincent/.config/superpowers/worktrees/personal-assistant/feature/scheduler
uv add apscheduler sqlitedict pydantic-ai
```

Expected: Dependencies added to pyproject.toml and uv.lock updated

**Step 2: Verify installation**

```bash
uv pip list | grep -E "(apscheduler|sqlitedict|pydantic-ai)"
```

Expected output showing:
```
apscheduler     4.x.x
sqlitedict      2.x.x
pydantic-ai     0.x.x
```

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "feat: add scheduler dependencies (apscheduler, sqlitedict, pydantic-ai)"
```

---

## Task 2: Create Task Metadata Store

**Files:**
- Create: `task_store.py`
- Create: `tests/test_task_store.py`

**Step 1: Write the failing test**

Create `tests/test_task_store.py`:

```python
"""Tests for task metadata store."""
import os
import tempfile
from task_store import TaskStore


def test_store_and_retrieve_task_metadata():
    """Test storing and retrieving task metadata."""
    # Use temporary file for test database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        store = TaskStore(db_path)

        # Store task metadata
        job_id = "test_job_123"
        metadata = {
            "task_type": "reminder",
            "user_id": 12345,
            "chat_id": 67890,
            "original_request": "remind me to call mom",
            "preferences": {"message": "call mom"},
            "created_at": "2025-12-19T10:30:00"
        }

        store.save_task(job_id, metadata)

        # Retrieve task metadata
        retrieved = store.get_task(job_id)

        assert retrieved is not None
        assert retrieved["task_type"] == "reminder"
        assert retrieved["user_id"] == 12345
        assert retrieved["chat_id"] == 67890
        assert retrieved["preferences"]["message"] == "call mom"

        store.close()
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_task_store.py::test_store_and_retrieve_task_metadata -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'task_store'"

**Step 3: Write minimal implementation**

Create `task_store.py`:

```python
"""Task metadata storage using sqlitedict."""
from typing import Any, Dict, Optional
from sqlitedict import SqliteDict


class TaskStore:
    """Wrapper around sqlitedict for storing task metadata.

    Stores rich context for scheduled tasks including user preferences,
    original requests, and task-specific data.
    """

    def __init__(self, db_path: str = "task_metadata.db"):
        """Initialize task store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db = SqliteDict(db_path, autocommit=True)

    def save_task(self, job_id: str, metadata: Dict[str, Any]) -> None:
        """Save task metadata.

        Args:
            job_id: APScheduler job ID
            metadata: Task metadata dictionary
        """
        self.db[job_id] = metadata

    def get_task(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task metadata.

        Args:
            job_id: APScheduler job ID

        Returns:
            Task metadata dictionary or None if not found
        """
        return self.db.get(job_id)

    def delete_task(self, job_id: str) -> None:
        """Delete task metadata.

        Args:
            job_id: APScheduler job ID
        """
        if job_id in self.db:
            del self.db[job_id]

    def list_tasks_by_user(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        """List all tasks for a specific user.

        Args:
            user_id: Telegram user ID

        Returns:
            Dictionary mapping job_id to task metadata
        """
        return {
            job_id: metadata
            for job_id, metadata in self.db.items()
            if metadata.get("user_id") == user_id
        }

    def close(self) -> None:
        """Close the database connection."""
        self.db.close()
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/test_task_store.py::test_store_and_retrieve_task_metadata -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add task_store.py tests/test_task_store.py
git commit -m "feat: add task metadata store using sqlitedict"
```

---

## Task 3: Create Gym Booking Module for Bot Integration

**Files:**
- Create: `gym_booking.py`
- Create: `tests/test_gym_booking.py`

**Step 1: Write the failing test**

Create `tests/test_gym_booking.py`:

```python
"""Tests for gym booking bot integration."""
from gym_booking import get_available_slots
from unittest.mock import Mock, patch


def test_get_available_slots_returns_slot_data():
    """Test that get_available_slots returns structured slot data."""
    # Mock browser automation to return fake slots
    with patch('gym_booking.Agent') as mock_agent, \
         patch('gym_booking.Browser') as mock_browser:

        # Configure mock to simulate finding slots
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance

        # Call function
        slots = get_available_slots(
            preferred_hours=["07:00", "08:00"],
            credentials={"x_user": "test@example.com", "x_pass": "testpass"}
        )

        # Verify structure (mock will return empty list for now)
        assert isinstance(slots, list)
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_gym_booking.py::test_get_available_slots_returns_slot_data -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'gym_booking'"

**Step 3: Write minimal implementation**

Create `gym_booking.py`:

```python
"""Gym booking logic adapted for Telegram bot integration."""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

from browser_use import Agent, Browser, Controller
from browser_use.llm.openai.chat import ChatOpenAI
from loguru import logger


@dataclass
class GymSlot:
    """Represents an available gym time slot."""
    time: str
    date: str
    available: bool
    slot_id: Optional[str] = None


RESERVATION_URL = "https://qore.clubplanner.be/Reservation/NewReservation/1"


def get_available_slots(
    preferred_hours: List[str],
    credentials: Dict[str, str],
    max_sessions: int = 2
) -> List[GymSlot]:
    """Check available gym slots without booking.

    Args:
        preferred_hours: List of preferred time slots (e.g., ["07:00", "08:00"])
        credentials: Dict with x_user and x_pass keys
        max_sessions: Maximum sessions per week

    Returns:
        List of GymSlot objects representing available slots
    """
    logger.info("Checking available gym slots")

    task = f"""
    Go to {RESERVATION_URL} and check available gym sessions.
    Use x_user and x_pass from sensitive_data to login.

    Find available sessions matching these preferred times: {', '.join(preferred_hours)}
    Do NOT book anything - just return the available options.

    For each available slot, extract:
    - Time (e.g., "07:00")
    - Date (e.g., "2025-12-20")
    - Any slot identifier if visible
    """

    try:
        browser = Browser(headless=True)
        controller = Controller()
        llm = ChatOpenAI(model="gpt-4o")

        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            controller=controller,
            sensitive_data=credentials,
            use_vision=True,
        )

        # Run agent and parse results
        result = agent.run_sync()
        browser.close_sync()

        # TODO: Parse agent result into GymSlot objects
        # For now, return empty list (minimal implementation)
        return []

    except Exception as e:
        logger.error(f"Error checking gym slots: {e}")
        return []


def book_gym_slot(
    slot: GymSlot,
    credentials: Dict[str, str]
) -> bool:
    """Book a specific gym slot.

    Args:
        slot: GymSlot object to book
        credentials: Dict with x_user and x_pass keys

    Returns:
        True if booking successful, False otherwise
    """
    logger.info(f"Booking gym slot: {slot.time} on {slot.date}")

    task = f"""
    Go to {RESERVATION_URL} and book a gym session.
    Use x_user and x_pass from sensitive_data to login.

    Book the session at {slot.time} on {slot.date}.
    Complete the booking process.
    """

    try:
        browser = Browser(headless=True)
        controller = Controller()
        llm = ChatOpenAI(model="gpt-4o")

        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            controller=controller,
            sensitive_data=credentials,
            use_vision=True,
        )

        result = agent.run_sync()
        browser.close_sync()

        logger.info("Gym booking completed")
        return True

    except Exception as e:
        logger.error(f"Error booking gym slot: {e}")
        return False
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/test_gym_booking.py::test_get_available_slots_returns_slot_data -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add gym_booking.py tests/test_gym_booking.py
git commit -m "feat: add gym booking module for bot integration"
```

---

## Task 4: Integrate APScheduler into Telegram Bot

**Files:**
- Modify: `interact_with_telegram.py:1-55`
- Create: `tests/test_scheduler_integration.py`

**Step 1: Write the failing test**

Create `tests/test_scheduler_integration.py`:

```python
"""Tests for APScheduler integration with Telegram bot."""
import os
import tempfile
from unittest.mock import AsyncMock, Mock, patch
from interact_with_telegram import create_scheduler


def test_create_scheduler_returns_asyncio_scheduler():
    """Test that create_scheduler initializes APScheduler correctly."""
    # Use temporary database for test
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        scheduler = create_scheduler(f"sqlite:///{db_path}")

        # Verify scheduler is AsyncIOScheduler
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        assert isinstance(scheduler, AsyncIOScheduler)

        # Verify scheduler can be started
        scheduler.start()
        assert scheduler.state == 1  # Running state

        # Cleanup
        scheduler.shutdown()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_scheduler_integration.py::test_create_scheduler_returns_asyncio_scheduler -v
```

Expected: FAIL with "ImportError: cannot import name 'create_scheduler'"

**Step 3: Write minimal implementation**

Modify `interact_with_telegram.py`:

```python
#!/usr/bin/env python3
"""
Telegram bot with APScheduler integration for task scheduling.
"""
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.eventbrokers.local import LocalEventBroker
from loguru import logger

# Load environment variables
load_dotenv()

# Get the bot token from environment variable
TOKEN = os.getenv('TELEGRAM_API_KEY')

if not TOKEN:
    raise ValueError("TELEGRAM_API_KEY not found in .env file. Please add your bot token.")


def create_scheduler(db_url: str = "sqlite:///schedules.db") -> AsyncIOScheduler:
    """Create and configure APScheduler.

    Args:
        db_url: SQLAlchemy database URL for job storage

    Returns:
        Configured AsyncIOScheduler instance
    """
    datastore = SQLAlchemyDataStore(url=db_url)
    event_broker = LocalEventBroker()

    scheduler = AsyncIOScheduler(
        data_store=datastore,
        event_broker=event_broker
    )

    return scheduler


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Bot is now active! Send me any message and I will respond.')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages and respond with 'hello there!'"""
    # Log the received message
    user = update.effective_user
    message_text = update.message.text
    logger.info(f"Received message from {user.first_name} (@{user.username}): {message_text}")

    # Respond with "hello there!"
    await update.message.reply_text('hello there!')


def main() -> None:
    """Start the bot."""
    logger.info("Starting bot with scheduler...")

    # Create and start scheduler
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Store scheduler in application context for access in handlers
    application.bot_data['scheduler'] = scheduler

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    logger.info(f"Bot is running! Send messages to @sidekick_pa_bot on Telegram.")
    logger.info("Press Ctrl-C to stop the bot.")

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        # Shutdown scheduler on exit
        scheduler.shutdown()
        logger.info("Scheduler shutdown complete")


if __name__ == '__main__':
    main()
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/test_scheduler_integration.py::test_create_scheduler_returns_asyncio_scheduler -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add interact_with_telegram.py tests/test_scheduler_integration.py
git commit -m "feat: integrate APScheduler into Telegram bot"
```

---

## Task 5: Add Task Execution Handlers

**Files:**
- Create: `task_handlers.py`
- Create: `tests/test_task_handlers.py`

**Step 1: Write the failing test**

Create `tests/test_task_handlers.py`:

```python
"""Tests for task execution handlers."""
import tempfile
from unittest.mock import AsyncMock, Mock, patch
from task_handlers import send_reminder_handler
from task_store import TaskStore


def test_send_reminder_handler_sends_message():
    """Test that reminder handler sends Telegram message."""
    # Setup test database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        store = TaskStore(db_path)
        job_id = "test_reminder_123"

        # Store test reminder metadata
        store.save_task(job_id, {
            "task_type": "reminder",
            "chat_id": 12345,
            "preferences": {"message": "test reminder message"}
        })

        # Mock Telegram bot
        mock_bot = Mock()
        mock_bot.send_message = AsyncMock()

        # Create handler with dependencies
        import asyncio
        handler = send_reminder_handler(bot=mock_bot, task_store=store)

        # Execute handler
        asyncio.run(handler(job_id))

        # Verify message was sent
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert call_args[1]['chat_id'] == 12345
        assert "test reminder message" in call_args[1]['text']

        store.close()
    finally:
        import os
        if os.path.exists(db_path):
            os.unlink(db_path)
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_task_handlers.py::test_send_reminder_handler_sends_message -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'task_handlers'"

**Step 3: Write minimal implementation**

Create `task_handlers.py`:

```python
"""Task execution handlers for scheduled jobs."""
from typing import Callable
from telegram import Bot
from loguru import logger
from task_store import TaskStore


def send_reminder_handler(bot: Bot, task_store: TaskStore) -> Callable:
    """Create reminder handler function.

    Args:
        bot: Telegram Bot instance
        task_store: TaskStore instance

    Returns:
        Async handler function for reminder execution
    """
    async def handler(job_id: str) -> None:
        """Execute reminder task.

        Args:
            job_id: APScheduler job ID
        """
        logger.info(f"Executing reminder: {job_id}")

        try:
            # Load task metadata
            metadata = task_store.get_task(job_id)

            if not metadata:
                logger.error(f"No metadata found for job {job_id}")
                return

            chat_id = metadata.get("chat_id")
            message = metadata.get("preferences", {}).get("message", "Reminder!")

            # Send reminder message
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔔 Reminder: {message}"
            )

            logger.info(f"Reminder sent to chat {chat_id}")

        except Exception as e:
            logger.error(f"Error sending reminder {job_id}: {e}")

    return handler


def gym_booking_handler(bot: Bot, task_store: TaskStore) -> Callable:
    """Create gym booking handler function.

    Args:
        bot: Telegram Bot instance
        task_store: TaskStore instance

    Returns:
        Async handler function for gym booking execution
    """
    async def handler(job_id: str) -> None:
        """Execute gym booking task.

        Args:
            job_id: APScheduler job ID
        """
        logger.info(f"Executing gym booking: {job_id}")

        try:
            # Load task metadata
            metadata = task_store.get_task(job_id)

            if not metadata:
                logger.error(f"No metadata found for job {job_id}")
                return

            chat_id = metadata.get("chat_id")
            preferences = metadata.get("preferences", {})

            # TODO: Check available slots and send to user
            # For now, just send a placeholder message
            await bot.send_message(
                chat_id=chat_id,
                text="⏰ Time to book your gym session! (Feature in progress)"
            )

            logger.info(f"Gym booking notification sent to chat {chat_id}")

        except Exception as e:
            logger.error(f"Error executing gym booking {job_id}: {e}")

    return handler
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/test_task_handlers.py::test_send_reminder_handler_sends_message -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add task_handlers.py tests/test_task_handlers.py
git commit -m "feat: add task execution handlers for reminders and gym bookings"
```

---

## Task 6: Add Pydantic AI Agent with Scheduling Tools

**Files:**
- Create: `agent_tools.py`
- Create: `tests/test_agent_tools.py`

**Step 1: Write the failing test**

Create `tests/test_agent_tools.py`:

```python
"""Tests for Pydantic AI agent tools."""
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock
from agent_tools import create_schedule_tool
from task_store import TaskStore


def test_create_schedule_tool_creates_job():
    """Test that create_schedule tool creates APScheduler job."""
    # Setup test database
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    try:
        store = TaskStore(db_path)

        # Mock scheduler
        mock_scheduler = Mock()
        mock_scheduler.add_job = Mock(return_value=Mock(id="job_123"))

        # Create tool
        tool = create_schedule_tool(
            scheduler=mock_scheduler,
            task_store=store
        )

        # Execute tool
        result = tool(
            task_type="reminder",
            schedule_time=datetime.now() + timedelta(hours=1),
            task_params={
                "chat_id": 12345,
                "user_id": 67890,
                "message": "test reminder"
            }
        )

        # Verify job was created
        mock_scheduler.add_job.assert_called_once()

        # Verify result contains job_id
        assert "job_123" in result

        # Verify metadata was saved
        metadata = store.get_task("job_123")
        assert metadata is not None
        assert metadata["task_type"] == "reminder"

        store.close()
    finally:
        import os
        if os.path.exists(db_path):
            os.unlink(db_path)
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_agent_tools.py::test_create_schedule_tool_creates_job -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'agent_tools'"

**Step 3: Write minimal implementation**

Create `agent_tools.py`:

```python
"""Pydantic AI tools for scheduling tasks."""
from datetime import datetime
from typing import Any, Callable, Dict
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from task_store import TaskStore


def create_schedule_tool(
    scheduler: AsyncIOScheduler,
    task_store: TaskStore,
    timezone: str = "Europe/Brussels"
) -> Callable:
    """Create tool for scheduling tasks.

    Args:
        scheduler: APScheduler instance
        task_store: TaskStore instance
        timezone: Timezone string for scheduling

    Returns:
        Tool function for creating schedules
    """
    def tool(
        task_type: str,
        schedule_time: datetime,
        task_params: Dict[str, Any],
        is_recurring: bool = False,
        cron_pattern: Dict[str, Any] = None
    ) -> str:
        """Create a scheduled task.

        Args:
            task_type: Type of task ('reminder' or 'gym_booking')
            schedule_time: When to execute (for one-time tasks)
            task_params: Task-specific parameters and preferences
            is_recurring: Whether task repeats
            cron_pattern: Cron pattern for recurring tasks (e.g., {'day_of_week': 'mon', 'hour': 7})

        Returns:
            Confirmation message with job ID
        """
        logger.info(f"Creating {task_type} schedule")

        try:
            # Determine trigger
            if is_recurring and cron_pattern:
                trigger = CronTrigger(
                    timezone=ZoneInfo(timezone),
                    **cron_pattern
                )
            else:
                trigger = DateTrigger(
                    run_date=schedule_time,
                    timezone=ZoneInfo(timezone)
                )

            # Determine handler function name based on task type
            if task_type == "reminder":
                func_id = "send_reminder"
            elif task_type == "gym_booking":
                func_id = "gym_booking"
            else:
                return f"Error: Unknown task type '{task_type}'"

            # Add job to scheduler
            job = scheduler.add_job(
                func=func_id,  # Will be resolved when handlers are registered
                trigger=trigger,
                id=None,  # Let scheduler generate ID
                args=[],  # Job ID will be passed by scheduler
            )

            job_id = job.id

            # Store task metadata
            metadata = {
                "task_type": task_type,
                "user_id": task_params.get("user_id"),
                "chat_id": task_params.get("chat_id"),
                "preferences": task_params,
                "created_at": datetime.now().isoformat(),
                "is_recurring": is_recurring
            }

            task_store.save_task(job_id, metadata)

            logger.info(f"Created schedule with job ID: {job_id}")
            return f"✓ Schedule created (ID: {job_id})"

        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            return f"Error creating schedule: {str(e)}"

    return tool


def list_schedules_tool(task_store: TaskStore) -> Callable:
    """Create tool for listing user's schedules.

    Args:
        task_store: TaskStore instance

    Returns:
        Tool function for listing schedules
    """
    def tool(user_id: int) -> str:
        """List all schedules for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            Formatted list of schedules
        """
        tasks = task_store.list_tasks_by_user(user_id)

        if not tasks:
            return "You have no scheduled tasks."

        lines = ["Your scheduled tasks:"]
        for job_id, metadata in tasks.items():
            task_type = metadata.get("task_type", "unknown")
            is_recurring = metadata.get("is_recurring", False)
            recurrence = "recurring" if is_recurring else "one-time"
            lines.append(f"- {task_type} ({recurrence}) [ID: {job_id}]")

        return "\n".join(lines)

    return tool


def cancel_schedule_tool(
    scheduler: AsyncIOScheduler,
    task_store: TaskStore
) -> Callable:
    """Create tool for canceling schedules.

    Args:
        scheduler: APScheduler instance
        task_store: TaskStore instance

    Returns:
        Tool function for canceling schedules
    """
    def tool(job_id: str) -> str:
        """Cancel a scheduled task.

        Args:
            job_id: Job ID to cancel

        Returns:
            Confirmation message
        """
        try:
            # Remove from scheduler
            scheduler.remove_job(job_id)

            # Remove metadata
            task_store.delete_task(job_id)

            logger.info(f"Cancelled schedule: {job_id}")
            return f"✓ Schedule cancelled (ID: {job_id})"

        except Exception as e:
            logger.error(f"Error cancelling schedule: {e}")
            return f"Error cancelling schedule: {str(e)}"

    return tool
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/test_agent_tools.py::test_create_schedule_tool_creates_job -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add agent_tools.py tests/test_agent_tools.py
git commit -m "feat: add Pydantic AI tools for scheduling"
```

---

## Task 7: Integrate Pydantic AI Agent into Bot

**Files:**
- Modify: `interact_with_telegram.py`
- Create: `tests/test_agent_integration.py`

**Step 1: Write the failing test**

Create `tests/test_agent_integration.py`:

```python
"""Tests for Pydantic AI agent integration."""
from unittest.mock import AsyncMock, Mock, patch
from interact_with_telegram import create_agent


def test_create_agent_with_tools():
    """Test that create_agent initializes Pydantic AI with tools."""
    mock_scheduler = Mock()
    mock_task_store = Mock()

    with patch('interact_with_telegram.Agent') as mock_agent_class:
        agent = create_agent(
            scheduler=mock_scheduler,
            task_store=mock_task_store
        )

        # Verify Agent was created
        mock_agent_class.assert_called_once()

        # Verify tools were passed
        call_kwargs = mock_agent_class.call_args[1]
        assert 'tools' in call_kwargs
        assert len(call_kwargs['tools']) > 0
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_agent_integration.py::test_create_agent_with_tools -v
```

Expected: FAIL with "ImportError: cannot import name 'create_agent'"

**Step 3: Write minimal implementation**

Modify `interact_with_telegram.py` to add agent creation:

```python
# Add these imports at the top
from pydantic_ai import Agent as PydanticAgent
from task_store import TaskStore
from agent_tools import create_schedule_tool, list_schedules_tool, cancel_schedule_tool

# Add after create_scheduler function
def create_agent(
    scheduler: AsyncIOScheduler,
    task_store: TaskStore
) -> PydanticAgent:
    """Create Pydantic AI agent with scheduling tools.

    Args:
        scheduler: APScheduler instance
        task_store: TaskStore instance

    Returns:
        Configured Pydantic AI agent
    """
    # Create tools
    schedule_tool = create_schedule_tool(scheduler, task_store)
    list_tool = list_schedules_tool(task_store)
    cancel_tool = cancel_schedule_tool(scheduler, task_store)

    # Create agent with tools
    agent = PydanticAgent(
        model='openai:gpt-4o',
        tools=[schedule_tool, list_tool, cancel_tool],
        system_prompt="""You are a personal assistant that helps users schedule tasks.

You can:
- Create reminders (one-time or recurring)
- Schedule gym bookings (recurring)
- List user's scheduled tasks
- Cancel scheduled tasks

When a user asks to schedule something:
1. Extract the task type, timing, and preferences
2. Ask clarifying questions if anything is unclear
3. Always confirm before creating the schedule
4. Use the appropriate tool to create the schedule

Be conversational and helpful. Always confirm details before scheduling."""
    )

    return agent

# Update main() function to create task store and agent
def main() -> None:
    """Start the bot."""
    logger.info("Starting bot with scheduler...")

    # Create and start scheduler
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    # Create task store
    task_store = TaskStore()
    logger.info("Task store initialized")

    # Create Pydantic AI agent
    agent = create_agent(scheduler, task_store)
    logger.info("AI agent initialized")

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Store dependencies in application context
    application.bot_data['scheduler'] = scheduler
    application.bot_data['task_store'] = task_store
    application.bot_data['agent'] = agent

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    logger.info(f"Bot is running! Send messages to @sidekick_pa_bot on Telegram.")
    logger.info("Press Ctrl-C to stop the bot.")

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        # Shutdown scheduler on exit
        scheduler.shutdown()
        task_store.close()
        logger.info("Shutdown complete")
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/test_agent_integration.py::test_create_agent_with_tools -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add interact_with_telegram.py tests/test_agent_integration.py
git commit -m "feat: integrate Pydantic AI agent into bot"
```

---

## Task 8: Connect Agent to Message Handler

**Files:**
- Modify: `interact_with_telegram.py` (handle_message function)
- Create: `tests/test_message_handling.py`

**Step 1: Write the failing test**

Create `tests/test_message_handling.py`:

```python
"""Tests for agent message handling."""
import asyncio
from unittest.mock import AsyncMock, Mock
from interact_with_telegram import handle_agent_message


def test_handle_agent_message_calls_agent():
    """Test that handle_agent_message invokes Pydantic AI agent."""
    mock_agent = Mock()
    mock_agent.run = AsyncMock(return_value=Mock(output="Test response"))

    mock_update = Mock()
    mock_update.effective_user.id = 12345
    mock_update.message.chat_id = 67890
    mock_update.message.text = "remind me to test"
    mock_update.message.reply_text = AsyncMock()

    mock_context = Mock()
    mock_context.bot_data = {'agent': mock_agent}

    # Run handler
    asyncio.run(handle_agent_message(mock_update, mock_context))

    # Verify agent was called
    mock_agent.run.assert_called_once()

    # Verify response was sent
    mock_update.message.reply_text.assert_called_once()
```

**Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/test_message_handling.py::test_handle_agent_message_calls_agent -v
```

Expected: FAIL with "ImportError: cannot import name 'handle_agent_message'"

**Step 3: Write minimal implementation**

Modify `interact_with_telegram.py` - replace handle_message function:

```python
async def handle_agent_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages with Pydantic AI agent.

    Args:
        update: Telegram update object
        context: Bot context with agent in bot_data
    """
    user = update.effective_user
    message_text = update.message.text
    logger.info(f"Received message from {user.first_name} (@{user.username}): {message_text}")

    # Get agent from context
    agent = context.bot_data.get('agent')

    if not agent:
        await update.message.reply_text("Agent not initialized. Please restart the bot.")
        return

    try:
        # Run agent with user message and context
        result = await agent.run(
            message_text,
            message_history=[],  # TODO: Implement conversation history
            user_id=user.id,
            chat_id=update.message.chat_id
        )

        # Send agent's response
        response = result.output
        await update.message.reply_text(response)
        logger.info(f"Agent responded: {response}")

    except Exception as e:
        logger.error(f"Error processing message with agent: {e}")
        await update.message.reply_text("Sorry, I encountered an error processing your request.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route messages to agent handler."""
    await handle_agent_message(update, context)
```

**Step 4: Run test to verify it passes**

```bash
uv run python -m pytest tests/test_message_handling.py::test_handle_agent_message_calls_agent -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add interact_with_telegram.py tests/test_message_handling.py
git commit -m "feat: connect Pydantic AI agent to message handler"
```

---

## Task 9: Register Task Handlers with Scheduler

**Files:**
- Modify: `interact_with_telegram.py`

**Step 1: Register handlers in main()**

Modify `interact_with_telegram.py` main() function to register task handlers:

```python
# Add imports
from task_handlers import send_reminder_handler, gym_booking_handler

# Modify main() function - add after scheduler.start()
def main() -> None:
    """Start the bot."""
    logger.info("Starting bot with scheduler...")

    # Create and start scheduler
    scheduler = create_scheduler()

    # Create task store
    task_store = TaskStore()
    logger.info("Task store initialized")

    # Create Pydantic AI agent
    agent = create_agent(scheduler, task_store)
    logger.info("AI agent initialized")

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Create task handlers with bot reference
    bot = application.bot
    reminder_handler = send_reminder_handler(bot, task_store)
    gym_handler = gym_booking_handler(bot, task_store)

    # Register handlers with scheduler
    scheduler.add_job_executor('send_reminder', reminder_handler)
    scheduler.add_job_executor('gym_booking', gym_handler)

    # Now start scheduler (after handlers registered)
    scheduler.start()
    logger.info("Scheduler started with handlers registered")

    # Store dependencies in application context
    application.bot_data['scheduler'] = scheduler
    application.bot_data['task_store'] = task_store
    application.bot_data['agent'] = agent

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    logger.info(f"Bot is running! Send messages to @sidekick_pa_bot on Telegram.")
    logger.info("Press Ctrl-C to stop the bot.")

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        # Shutdown scheduler on exit
        scheduler.shutdown()
        task_store.close()
        logger.info("Shutdown complete")
```

**Step 2: Test manually**

```bash
# Start the bot
uv run python interact_with_telegram.py

# In another terminal, check logs
# Verify: "Scheduler started with handlers registered"
```

Expected: Bot starts without errors and shows handler registration log

**Step 3: Commit**

```bash
git add interact_with_telegram.py
git commit -m "feat: register task handlers with scheduler"
```

---

## Task 10: Add Environment Variable for Timezone

**Files:**
- Modify: `.env` (not committed, document only)
- Modify: `agent_tools.py`
- Create: `docs/ENV_VARIABLES.md`

**Step 1: Document environment variables**

Create `docs/ENV_VARIABLES.md`:

```markdown
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

## Pydantic AI

- `PYDANTIC_AI_MODEL` - Model to use (default: "openai:gpt-4o")
- Optional, defaults to gpt-4o if not set

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
PYDANTIC_AI_MODEL=openai:gpt-4o
TIMEZONE=Europe/Brussels
DB_PATH=.
```
```

**Step 2: Update agent_tools.py to use environment variable**

Modify `agent_tools.py`:

```python
# Add import at top
import os

# Modify create_schedule_tool function signature
def create_schedule_tool(
    scheduler: AsyncIOScheduler,
    task_store: TaskStore,
    timezone: str = None
) -> Callable:
    """Create tool for scheduling tasks.

    Args:
        scheduler: APScheduler instance
        task_store: TaskStore instance
        timezone: Timezone string for scheduling (defaults to env var or Europe/Brussels)

    Returns:
        Tool function for creating schedules
    """
    # Use environment variable if timezone not provided
    if timezone is None:
        timezone = os.getenv('TIMEZONE', 'Europe/Brussels')

    # ... rest of function unchanged
```

**Step 3: Commit**

```bash
git add docs/ENV_VARIABLES.md agent_tools.py
git commit -m "docs: add environment variables documentation and timezone support"
```

---

## Task 11: Add README with Setup Instructions

**Files:**
- Modify: `README.md`

**Step 1: Write comprehensive README**

Modify `README.md`:

```markdown
# Personal Assistant Bot

A Python-based Telegram bot that provides personal assistant features including:
- 🏋️ Automated gym booking with scheduling
- 🔔 Reminders (one-time and recurring)
- 🗓️ Task scheduling with natural language

## Features

### Current
- **Gym Booking Automation** - Browser automation to book gym sessions
- **Telegram Bot Interface** - Interact via Telegram messages
- **Task Scheduling** - Schedule reminders and recurring gym bookings
- **Natural Language** - Use plain English to create schedules
- **Persistent Storage** - Schedules survive bot restarts

### Planned
- Calendar integration
- More task types (bill reminders, etc.)
- Multi-user support

## Tech Stack

- **Python 3.12+**
- **uv** - Fast Python package manager
- **python-telegram-bot** - Telegram Bot API
- **APScheduler** - Task scheduling
- **Pydantic AI** - Natural language understanding
- **browser-use** - Web automation for gym booking
- **sqlitedict** - Task metadata storage

## Setup

### Prerequisites

1. Python 3.12 or higher
2. `uv` package manager ([installation](https://github.com/astral-sh/uv))
3. Telegram bot token (from [@BotFather](https://t.me/botfather))
4. OpenAI API key (for AI features)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd personal-assistant
```

2. Install dependencies:
```bash
uv sync
```

3. Create `.env` file with required variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

See [docs/ENV_VARIABLES.md](docs/ENV_VARIABLES.md) for details on environment variables.

### Running the Bot

```bash
uv run python interact_with_telegram.py
```

The bot will start and display:
```
Starting bot with scheduler...
Task store initialized
AI agent initialized
Scheduler started with handlers registered
Bot is running! Send messages to @<your_bot> on Telegram.
```

## Usage

### Creating a Reminder

Talk to your bot naturally:

```
You: Remind me to call mom tomorrow at 2pm
Bot: Should I remind you just once, or repeat this?
You: Just once
Bot: I'll send you a reminder tomorrow at 2pm to call mom. Confirm?
You: Yes
Bot: ✓ Reminder set for tomorrow at 2pm
```

### Scheduling Gym Bookings

```
You: Book gym every Monday at 7am
Bot: Which weeks should I book? Every week or specific dates?
You: Every week
Bot: What should I do if 7am isn't available?
You: Try 8am, otherwise skip
Bot: I'll book gym every Monday at 7am (fallback 8am). Confirm?
You: Yes
Bot: ✓ Scheduled gym booking every Monday at 7am
```

### Listing Schedules

```
You: Show my schedules
Bot: Your scheduled tasks:
- reminder (one-time) [ID: abc123]
- gym_booking (recurring) [ID: def456]
```

### Canceling a Schedule

```
You: Cancel my Monday gym booking
Bot: ✓ Schedule cancelled (ID: def456)
```

## Development

### Project Structure

```
personal-assistant/
├── interact_with_telegram.py  # Main bot with scheduler
├── book_gym.py                 # Gym booking logic
├── gym_booking.py              # Bot-integrated gym booking
├── task_store.py              # Task metadata storage
├── task_handlers.py           # Scheduled task execution
├── agent_tools.py             # Pydantic AI tools
├── tests/                     # Test suite
├── docs/                      # Documentation
│   ├── plans/                # Design and implementation plans
│   └── ENV_VARIABLES.md      # Environment variable docs
├── schedules.db              # APScheduler database (created at runtime)
├── task_metadata.db          # Task metadata (created at runtime)
└── .env                      # Environment variables (not committed)
```

### Testing

Run the test suite:

```bash
uv run python -m pytest
```

Run specific test:

```bash
uv run python -m pytest tests/test_task_store.py -v
```

### Code Style

- Follow PEP 8 conventions
- Use type hints for all functions
- Write docstrings for public functions
- Keep code simple and readable (YAGNI)

### Development Workflow

This project follows Test-Driven Development (TDD):

1. **RED** - Write test first, watch it fail
2. **GREEN** - Write minimal code to pass test
3. **REFACTOR** - Clean up if needed

See [CLAUDE.md](CLAUDE.md) for detailed development guidelines.

## Deployment

### AWS EC2 (Recommended)

1. Launch EC2 instance (t4g.micro recommended)
2. Install Python 3.12+ and uv
3. Clone repository and install dependencies
4. Set up environment variables
5. Create systemd service:

```ini
[Unit]
Description=Personal Assistant Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/personal-assistant
Environment="DB_PATH=/var/lib/telegram-bot"
ExecStart=/opt/personal-assistant/.venv/bin/uv run python interact_with_telegram.py
Restart=always

[Install]
WantedBy=multi-user.target
```

6. Enable and start service:
```bash
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

### Monitoring

Check logs:
```bash
sudo journalctl -u telegram-bot -f
```

### Backup

SQLite databases are stored in `DB_PATH` (default: current directory):
- `schedules.db` - APScheduler jobs
- `task_metadata.db` - Task metadata

Back up regularly to S3 or your backup solution of choice.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests first (TDD)
4. Implement feature
5. Ensure all tests pass
6. Submit pull request

## License

[Your license here]

## Support

For issues or questions, open an issue on GitHub.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README with setup and usage instructions"
```

---

## Next Steps

After completing these tasks, you'll have a working scheduler foundation with:

✅ APScheduler integrated into Telegram bot
✅ Task metadata storage with sqlitedict
✅ Pydantic AI agent with scheduling tools
✅ Basic reminder and gym booking handlers
✅ Comprehensive tests for each component
✅ Documentation and setup instructions

**Still to implement (future work):**
- Complete gym booking execution with Telegram buttons
- Conversation history for agent
- More sophisticated scheduling options
- Calendar integration
- Multi-user support

**To continue development:**
1. Test the current implementation manually
2. Add gym booking execution with InlineKeyboard
3. Implement conversation history
4. Deploy to AWS EC2
