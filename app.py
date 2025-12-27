#!/usr/bin/env python3

import datetime
import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
)
from browser_use import Agent, Browser, Controller
from browser_use.agent.views import ActionResult
from browser_use.llm.openai.chat import ChatOpenAI
from pydantic_ai import Agent as PydanticAgent, RunContext
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    SystemPromptPart
)
from pydantic_core import to_jsonable_python
from sqlitedict import SqliteDict

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_API_KEY')

if not TOKEN:
    raise ValueError("TELEGRAM_API_KEY not found in .env file")

# Database for user chat history (single connection for entire app lifecycle)
DB_PATH = "app.db"
user_db = SqliteDict(DB_PATH, autocommit=True)

# Scheduler imports
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from schedules_store import SchedulesStore
from typing import Any
import json

# Scheduler configuration
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Europe/Brussels"))

def create_scheduler() -> AsyncIOScheduler:
    """
    Create and configure APScheduler instance.

    Returns:
        Configured AsyncIOScheduler instance
    """
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    return scheduler

# Initialize global scheduler and schedules store (using same DB_PATH as user_db)
scheduler = create_scheduler()
schedules_store = SchedulesStore(DB_PATH, table_name="schedules")


async def execute_scheduled_task(schedule_id: str) -> None:
    """
    Execute a scheduled task based on its configuration.

    Args:
        schedule_id: Schedule ID from schedules_store
    """
    # Load schedule metadata
    schedule = schedules_store.get_schedule(schedule_id)
    if not schedule:
        print(f"Error: No schedule found for {schedule_id}")
        return

    task_type = schedule["task_type"]
    chat_id = schedule["chat_id"]
    preferences = json.loads(schedule.get("preferences", "{}"))

    print(f"Executing {task_type} for schedule {schedule_id}, chat {chat_id}")
    print(f"Preferences: {preferences}")

    # Task-specific execution logic goes here
    # This will be implemented in later tasks
    # For now, just log that we would execute the task


async def create_schedule(
    user_id: int,
    chat_id: int,
    task_type: str,
    cron_hour: int,
    cron_minute: int = 0,
    cron_day_of_week: str | None = None,
    preferences: dict[str, Any] | None = None,
    original_request: str = ""
) -> str:
    """
    Create a generic recurring schedule for any task type.

    Args:
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        task_type: Type of task (e.g., 'gym_booking', 'reminder', etc.)
        cron_hour: Hour (0-23) for execution
        cron_minute: Minute (0-59) for execution
        cron_day_of_week: Day of week (mon, tue, wed, thu, fri, sat, sun) or None for daily
        preferences: Task-specific preferences
        original_request: Original natural language request

    Returns:
        Schedule ID
    """
    # Generate unique schedule ID
    import uuid
    schedule_id = f"{task_type}_{user_id}_{uuid.uuid4().hex[:8]}"

    # Store schedule in database
    schedules_store.create_schedule(
        schedule_id=schedule_id,
        user_id=user_id,
        chat_id=chat_id,
        task_type=task_type,
        cron_hour=cron_hour,
        cron_minute=cron_minute,
        cron_day_of_week=cron_day_of_week,
        preferences=json.dumps(preferences or {}),
        original_request=original_request
    )

    # Create cron trigger
    cron_params = {"hour": cron_hour, "minute": cron_minute, "timezone": TIMEZONE}
    if cron_day_of_week:
        cron_params["day_of_week"] = cron_day_of_week

    trigger = CronTrigger(**cron_params)

    # Add job to scheduler
    scheduler.add_job(
        execute_scheduled_task,
        trigger=trigger,
        args=[schedule_id],
        id=schedule_id
    )

    return schedule_id


def get_user_chat_history(user_id: int):
    """
    Get chat history for a user from the database.

    Args:
        user_id: Telegram user ID

    Returns:
        List of pydantic_ai messages or empty list if user is new
    """
    if user_id not in user_db:
        return []

    user_entry = user_db[user_id]
    chat_history_json = user_entry.get("chat_history", [])

    if not chat_history_json:
        return []

    # Convert from JSON to pydantic_ai messages
    return ModelMessagesTypeAdapter.validate_python(chat_history_json)


def save_user_chat_history(user_id: int, user_data: dict, messages):
    """
    Save user data and chat history to the database.

    Args:
        user_id: Telegram user ID
        user_data: Dictionary with user information (from telegram User object)
        messages: List of pydantic_ai messages to save
    """
    # Convert messages to JSON-serializable format
    messages_json = to_jsonable_python(messages)

    user_db[user_id] = {
        "user": user_data,
        "chat_history": messages_json
    }


def update_system_prompt_in_history(messages: list) -> list:
    """
    Update or add system prompt in message history.

    Args:
        messages: List of pydantic_ai messages
        new_system_prompt: The system prompt text to use

    Returns:
        Updated list of messages with current system prompt
    """
    if not messages:
        return messages

    # Check if first message has a system prompt
    first_msg = messages[0]
    if isinstance(first_msg, ModelRequest) and first_msg.parts:
        first_part = first_msg.parts[0]

        if isinstance(first_part, SystemPromptPart):
            # Replace existing system prompt
            new_parts = [SystemPromptPart(content=SYSTEM_PROMPT)] + list(first_msg.parts[1:])
            updated_first = ModelRequest(parts=new_parts)
            return [updated_first] + messages[1:]
        else:
            # Add system prompt at the beginning
            new_parts = [SystemPromptPart(content=SYSTEM_PROMPT)] + list(first_msg.parts)
            updated_first = ModelRequest(parts=new_parts)
            return [updated_first] + messages[1:]

    return messages


# System prompt for the orchestrator agent
SYSTEM_PROMPT = """You are a personal assistant bot that helps users with tasks like:
- Booking gym sessions (requires browser automation)
- Creating and managing recurring schedules for tasks
- Listing active schedules
- Canceling schedules
- General questions and conversation

When users ask to create schedules:
1. Extract the schedule details (task type, day of week, time)
2. Always confirm with the user before creating the schedule
3. Use create_user_schedule tool to create the schedule

Available task types:
- "gym_booking": Automated gym session booking
- "reminder": Simple reminder messages (implementation pending)
"""

# Create orchestrator agent (no deps needed for simple tools)
orchestrator_agent = PydanticAgent(
    'openai:gpt-4o-mini',
    system_prompt=SYSTEM_PROMPT
)

def create_telegram_aware_controller(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """
    Create a Controller with actions that can interact via Telegram.

    Args:
        chat_id: Telegram chat ID to send messages to
        context: Telegram Context object for conversation state
    """
    controller = Controller()

    # Store pending question and response in context
    if 'browser_state' not in context.user_data:
        context.user_data['browser_state'] = {
            'waiting_for_response': False,
            'pending_question': None,
            'user_response': None,
            'response_event': asyncio.Event()
        }

    @controller.registry.action('Ask the user a question via Telegram and wait for their response')
    async def ask_user(question: str) -> ActionResult:
        """
        Ask user a question via Telegram and wait for response.

        Args:
            question: The question to ask the user

        Returns:
            ActionResult with the user's response
        """
        state = context.user_data['browser_state']

        # Send question to Telegram using bot
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🤖 Browser Agent asks:\n\n{question}\n\n(Reply with your answer)"
        )

        # Mark that we're waiting for response
        state['waiting_for_response'] = True
        state['pending_question'] = question
        state['user_response'] = None
        state['response_event'].clear()

        # Wait for user to respond
        await state['response_event'].wait()


        # Get the response
        user_response = state['user_response']
        state['waiting_for_response'] = False
        state['pending_question'] = None

        memory = f"Asked user: '{question}'. User responded: '{user_response}'"
        return ActionResult(
            extracted_content=user_response,
            long_term_memory=memory
        )

    @controller.registry.action('Send the user a final update via Telegram before ending the session')
    async def send_final_update(message: str) -> ActionResult:
        """
        Send a final informational message to the user via Telegram (no response needed). 
        Typically when a session is booked, nothing is available or an error occurred.

        Args:
            message: The message to send to the user

        Returns:
            ActionResult confirming the message was sent
        """
        text = f"🤖 Browser Agent final update:\n\n{message}"
        await context.bot.send_message(
            chat_id=chat_id,
            text=text
        )

        return ActionResult(
                is_done=True,
                success=False,
                long_term_memory=text
        )

    return controller

async def run_browser_automation(chat_id: int, context: ContextTypes.DEFAULT_TYPE, task: str):
    """
    Run browser automation with Telegram integration.

    Args:
        chat_id: Telegram chat ID to send messages to
        context: Telegram Context object
        task: Task description for browser agent
    """
    await context.bot.send_message(chat_id=chat_id, text="🌐 Starting browser automation...")

    # Create browser and controller
    browser = Browser(headless=False)
    controller = create_telegram_aware_controller(chat_id, context)
    llm = ChatOpenAI(model="gpt-4o")

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        controller=controller,
        use_vision=True,
        sensitive_data= {"x_user": "vincent.v.claes@gmail.com", "x_pass": os.getenv("QORE_PASSWORD")}

    )

    try:
        # Run the agent (async)
        result = await agent.run()
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Browser automation completed!\n\nSteps taken: {len(result.history)}"
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Error during automation: {e}"
        )

LAUNCH_SIGNAL = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
    global LAUNCH_SIGNAL
    if LAUNCH_SIGNAL:
        @orchestrator_agent.tool
        async def dispatch_browser(ctx: RunContext, task_description: str) -> str:
            """Trigger browser automation for tasks like booking gym, browsing websites, etc.

            Args:
                task_description: Clear description of what the browser should do
            """
            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
            task_description = f"""
                Go to https://qore.clubplanner.be/ and log in using sensitive_data:
                - x_user = username
                - x_pass = password

                After login, navigate to:
                https://qore.clubplanner.be/Reservation/NewReservation/1

                ────────────────────────────────
                DOM FACTS (do not infer differently)
                ────────────────────────────────
                - The booking UI is contained in <div id="divnewreservation">.
                - Date selection buttons are <button> elements with class "cal_btn".
                - Disabled (unclickable) dates have class "disabled".
                - Clickable dates match: button.cal_btn:not(.disabled).
                - The day number is the numeric text directly inside the button.
                - The month is the text inside the child element <h6 class="hidden-xs"> (e.g. "dec", "jan").
                - The year is inferred from DOM order relative to <h4 class="has-warning"> headers
                (e.g. "januari 2026"): buttons after belong to that year; buttons before belong to the previous year.
                - Clicking a date triggers JavaScript getitems(...) and dynamically loads sessions.
                - Available sessions are rendered only inside <div id="divItems">.
                - The reservation/booking UI appears inside <div id="divreservationmember">.

                ────────────────────────────────
                PROCESS
                ────────────────────────────────
                1. Observe the page structure and confirm the presence of:
                - #divnewreservation
                - date buttons (button.cal_btn)
                - #divItems (initially empty)

                2. Determine the currently selected date from the UI.

                3. Read all sessions displayed inside #divItems and extract:
                - date
                - time
                - session name
                - amount of available spots

                4. List all sessions in the format:
                "date / time / session name / available spots"

                5. IF one or more sessions have at least one available spot:
                - Present only the available sessions to the user.
                - Number the list so the user can respond with a selection.
                - STOP and wait for explicit confirmation using ask_user.

                6. ONLY after explicit confirmation:
                - Proceed with booking the selected session.
                - Capture and report any popup or confirmation message.

                7. Verify the booking by navigating to:
                "Mijn Reservaties" (/Reservation/Reservations)
                - Confirm the booked session appears in the list.

                8. Send the final booking details using controller.send_final_update.

                9. IF no sessions on the selected date have availability:
                - Click the next button.cal_btn:not(.disabled) in DOM order.
                - Repeat steps 2–4.

                10. IF all available dates are exhausted:
                    - Use controller.send_final_update to report that no spots are available.

                ────────────────────────────────
                RULES
                ────────────────────────────────
                - Do NOT book anything without explicit confirmation via ask_user.
                - Do NOT assume sessions exist outside #divItems.
                - Do NOT infer dates from disabled buttons only.
                - Follow DOM order when iterating dates.
                - Stop immediately once a bookable session is found and presented to the user.

                TIP:
                It is currently {current_date}. Use the day number text and the month text inside
                each button.cal_btn to identify and select the correct date.
            """
            # Start browser automation in background so message handler stays free
            context.application.create_task(
                run_browser_automation(update.effective_chat.id, context, task_description)
            )
            return "Started browser automation in background"

        @orchestrator_agent.tool
        async def create_user_schedule(
            ctx: RunContext,
            task_type: str,
            schedule_description: str,
            cron_hour: int,
            cron_minute: int = 0,
            cron_day_of_week: str = None,
            preferences: dict = None
        ) -> str:
            """Create a recurring schedule for tasks like gym bookings or reminders.

            Args:
                task_type: Type of task (e.g., "gym_booking", "reminder")
                schedule_description: Human-readable description (e.g., "every Monday at 7am")
                cron_hour: Hour (0-23) for execution
                cron_minute: Minute (0-59) for execution (default: 0)
                cron_day_of_week: Day of week (mon, tue, wed, thu, fri, sat, sun) or None for daily
                preferences: Optional task-specific preferences (e.g., preferred time slots)

            Returns:
                Confirmation message with schedule ID
            """
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id

            try:
                schedule_id = await create_schedule(
                    user_id=user_id,
                    chat_id=chat_id,
                    task_type=task_type,
                    cron_hour=cron_hour,
                    cron_minute=cron_minute,
                    cron_day_of_week=cron_day_of_week,
                    preferences=preferences or {},
                    original_request=schedule_description
                )

                return f"✓ Schedule created! ID: {schedule_id}\n{schedule_description}"
            except Exception as e:
                return f"Error creating schedule: {e}"

        @orchestrator_agent.tool
        async def list_user_schedules(ctx: RunContext) -> str:
            """List all active schedules for the current user.

            Returns:
                Formatted list of schedules or message if none exist
            """
            user_id = update.effective_user.id
            schedules = schedules_store.list_schedules_for_user(user_id)

            if not schedules:
                return "You have no active schedules."

            lines = ["Your active schedules:\n"]
            for schedule in schedules:
                schedule_id = schedule["schedule_id"]
                task_type = schedule["task_type"]
                original_request = schedule["original_request"]

                # Get next run time from scheduler
                job = scheduler.get_job(schedule_id)
                if job:
                    next_run = job.next_fire_time
                    next_run_str = next_run.strftime('%Y-%m-%d %H:%M %Z') if next_run else "Not scheduled"
                else:
                    next_run_str = "Job not found in scheduler"

                lines.append(f"• {original_request}")
                lines.append(f"  Type: {task_type}")
                lines.append(f"  ID: {schedule_id}")
                lines.append(f"  Next run: {next_run_str}")
                lines.append("")

            return "\n".join(lines)

        @orchestrator_agent.tool
        async def cancel_user_schedule(ctx: RunContext, schedule_id: str) -> str:
            """Cancel a scheduled task.

            Args:
                schedule_id: The schedule ID to cancel (from list_user_schedules)

            Returns:
                Confirmation message
            """
            user_id = update.effective_user.id

            # Verify schedule belongs to user
            schedule = schedules_store.get_schedule(schedule_id)
            if not schedule:
                return f"Error: Schedule {schedule_id} not found"

            if schedule["user_id"] != user_id:
                return "Error: You can only cancel your own schedules"

            # Remove from scheduler and database
            try:
                scheduler.remove_job(schedule_id)
            except Exception as e:
                print(f"Warning: Could not remove job from scheduler: {e}")

            deleted = schedules_store.delete_schedule(schedule_id)

            if deleted:
                return f"✓ Schedule {schedule_id} cancelled successfully"
            else:
                return f"Error: Could not delete schedule {schedule_id}"

        LAUNCH_SIGNAL = False
            

    user = update.effective_user
    message_text = update.message.text
    print(f"Received from {user.first_name} ({user.id}): {message_text}")

    # Check if browser is waiting for response
    if 'browser_state' in context.user_data:
        state = context.user_data['browser_state']
        if state.get('waiting_for_response'):
            # This is a response to browser agent's question
            print(f"Forwarding response to browser: {message_text}")
            state['user_response'] = message_text
            state['response_event'].set()
            return

    # Load chat history for this user
    user_id = user.id
    chat_history = get_user_chat_history(user_id)
    # Update system prompt in history to ensure latest prompt is used
    chat_history = update_system_prompt_in_history(chat_history)

    # Use orchestrator agent to decide what to do
    print("🤔 Orchestrator agent analyzing message...")
    result = await orchestrator_agent.run(message_text, message_history=chat_history)

    # Save updated chat history (includes both user message and agent response)
    user_data = {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
    }
    all_messages = result.all_messages()
    save_user_chat_history(user_id, user_data, all_messages)

    # Extract the tool result (agent returns the last tool call result as output)
    output = result.output
    await update.message.reply_text(output)



def main() -> None:
    """Start the bot."""
    print("Starting Telegram bot with scheduler...")

    # Start scheduler
    scheduler.start()
    print(f"✓ Scheduler started (timezone: {TIMEZONE})")

    # Create application
    application = Application.builder().token(TOKEN).concurrent_updates(False).build()

    # Add message handler
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Run the bot
    print("Bot is running! Send messages to interact.")
    print("Press Ctrl-C to stop.")

    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    finally:
        # Shutdown scheduler on exit
        scheduler.shutdown(wait=True)
        schedules_store.close()
        print("✓ Scheduler stopped")


if __name__ == '__main__':
    main()
