#!/usr/bin/env python3

import asyncio
import datetime
import os
from textwrap import dedent
from zoneinfo import ZoneInfo

from apscheduler.job import Job as APSJob
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from browser_use import Agent, Browser, Controller
from browser_use.agent.views import ActionResult
from browser_use.llm.openai.chat import ChatOpenAI
from dotenv import load_dotenv
from loguru import logger
from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import RunContext
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    SystemPromptPart,
)
from pydantic_core import to_jsonable_python
from sqlitedict import SqliteDict
from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    JobQueue,
    MessageHandler,
    filters,
)
from telegram.ext._jobqueue import Job

from personal_assistant.database import DB_PATH


# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_API_KEY")
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"

if not TOKEN:
    raise ValueError("TELEGRAM_API_KEY not found in .env file")

# Database for user chat history (single connection for entire app lifecycle)
user_db = SqliteDict(DB_PATH, autocommit=True)


def get_user_chat_history(user_id: int):
    """
    Get chat history for a user from the database.

    Args:
        user_id: Telegram user ID

    Returns:
        List of pydantic_ai messages or empty list if user is new
    """
    logger.debug(f"Retrieving chat history for user_id={user_id}")
    if user_id not in user_db:
        logger.info(f"No chat history found for user_id={user_id} (new user)")
        return []

    user_entry = user_db[user_id]
    chat_history_json = user_entry.get("chat_history", [])

    if not chat_history_json:
        logger.debug(f"Chat history empty for user_id={user_id}")
        return []

    # Convert from JSON to pydantic_ai messages
    messages = ModelMessagesTypeAdapter.validate_python(chat_history_json)
    logger.debug(f"Loaded {len(messages)} messages from history for user_id={user_id}")
    return messages


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

    user_db[user_id] = {"user": user_data, "chat_history": messages_json}


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
            new_parts = [SystemPromptPart(content=get_agent_system_prompt())] + list(
                first_msg.parts[1:]
            )
            updated_first = ModelRequest(parts=new_parts)
            return [updated_first] + messages[1:]
        else:
            # Add system prompt at the beginning
            new_parts = [SystemPromptPart(content=get_agent_system_prompt())] + list(
                first_msg.parts
            )
            updated_first = ModelRequest(parts=new_parts)
            return [updated_first] + messages[1:]

    return messages


def get_agent_system_prompt():
    return dedent(
        f"""
    You are a personal assistant bot. Brevity in responses is critical.

    Current datetime: {datetime.datetime.now()}

    RESPONSE RULES (MANDATORY):
    - Maximum 2-3 short sentences per response
    - Options: max 3-4 choices, one line each, numbered
    - No explanations unless asked
    - No greetings or filler words
    - Use defaults when reasonable, ask only what's essential

    Tools:
    - Gym: book_gym tool
    - Reminders: schedule_reminder tool
    """
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
    if "browser_state" not in context.user_data:
        context.user_data["browser_state"] = {
            "waiting_for_response": False,
            "pending_question": None,
            "user_response": None,
            "response_event": asyncio.Event(),
        }

    @controller.registry.action(
        "Ask the user a question via Telegram and wait for their response"
    )
    async def ask_user(question: str) -> ActionResult:
        """
        Ask user a question via Telegram and wait for response.

        Args:
            question: The question to ask the user

        Returns:
            ActionResult with the user's response
        """
        state = context.user_data["browser_state"]

        # Send question to Telegram using bot
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{question}",
        )

        # Mark that we're waiting for response
        state["waiting_for_response"] = True
        state["pending_question"] = question
        state["user_response"] = None
        state["response_event"].clear()

        # Wait for user to respond
        await state["response_event"].wait()

        # Get the response
        user_response = state["user_response"]
        state["waiting_for_response"] = False
        state["pending_question"] = None

        memory = f"Asked user: '{question}'. User responded: '{user_response}'"
        return ActionResult(extracted_content=user_response, long_term_memory=memory)

    @controller.registry.action(
        "Send the user a final update via Telegram before ending the session"
    )
    async def send_final_update(message: str) -> ActionResult:
        """
        Send a final informational message to the user via Telegram (no response needed).
        Typically when a session is booked, nothing is available or an error occurred.

        Args:
            message: The message to send to the user

        Returns:
            ActionResult confirming the message was sent
        """
        await context.bot.send_message(chat_id=chat_id, text=message)

        return ActionResult(is_done=True, success=False, long_term_memory=message)

    @controller.registry.action(
        "Stop the booking process when user requests to cancel or abort"
    )
    async def cancel_booking() -> ActionResult:
        """
        Cancel the current booking process when the user explicitly requests to stop.
        Use this when the user says things like "cancel", "stop", "never mind", "abort", etc.

        Returns:
            ActionResult indicating the process was cancelled
        """
        text = "🛑 Booking process cancelled as requested."
        await context.bot.send_message(chat_id=chat_id, text=text)

        return ActionResult(
            is_done=True,
            success=False,
            long_term_memory="User requested to cancel the booking process.",
        )

    return controller


async def run_browser_automation(
    chat_id: int, context: ContextTypes.DEFAULT_TYPE, task: str
):
    """
    Run browser automation with Telegram integration.

    Args:
        chat_id: Telegram chat ID to send messages to
        context: Telegram Context object
        task: Task description for browser agent
    """
    await context.bot.send_message(
        chat_id=chat_id, text="🔍 Looking for available sessions..."
    )

    # Create browser and controller
    browser = Browser(headless=BROWSER_HEADLESS)
    controller = create_telegram_aware_controller(chat_id, context)
    llm = ChatOpenAI(model="gpt-4.1")

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        controller=controller,
        use_vision=True,
        sensitive_data={
            "x_user": "vincent.v.claes@gmail.com",
            "x_pass": os.getenv("QORE_PASSWORD"),
        },
    )

    try:
        await agent.run()
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Error: {e}")


class PTBSQLiteJobStore(SQLAlchemyJobStore):
    """SQLite jobstore that makes telegram.ext.Job class storable."""

    def __init__(self, application: Application, url: str = "sqlite:///bot.db") -> None:
        """Initialize with Application instance and SQLite database path.

        Args:
            application: Application instance for CallbackContext recreation
            url: SQLite database URL (default: sqlite:///bot.db)
        """
        self.application = application
        super().__init__(url=url)

    @staticmethod
    def _prepare_job(job: APSJob) -> APSJob:
        """Prepare job for storage by extracting Telegram-specific data."""
        prepped_job = APSJob.__new__(APSJob)
        prepped_job.__setstate__(job.__getstate__())
        tg_job = Job.from_aps_job(job)
        prepped_job.args = (
            tg_job.name,
            tg_job.data,
            tg_job.chat_id,
            tg_job.user_id,
            tg_job.callback,
        )
        return prepped_job

    def _restore_job(self, job: APSJob) -> APSJob:
        """Restore Telegram-specific job data after loading from database."""
        name, data, chat_id, user_id, callback = job.args
        tg_job = Job(
            callback=callback,
            chat_id=chat_id,
            user_id=user_id,
            name=name,
            data=data,
        )
        job._modify(
            args=(
                self.application.job_queue,
                tg_job,
            )
        )
        return job

    def add_job(self, job: APSJob) -> None:
        """Persist newly added job to database."""
        job = self._prepare_job(job)
        super().add_job(job)

    def update_job(self, job: APSJob) -> None:
        """Update existing job in database."""
        job = self._prepare_job(job)
        super().update_job(job)

    def _reconstitute_job(self, job_state: bytes) -> APSJob:
        """Reconstruct job from pickled state retrieved from database."""
        job: APSJob = super()._reconstitute_job(job_state)
        return self._restore_job(job)


def _schedule_cron_job(
    job_queue: JobQueue,
    chat_id: int,
    message: str,
    cron_expression: str,
    timezone_str: str = "Europe/Brussels",
    start_datetime: datetime.datetime | None = None,
    end_datetime: datetime.datetime | None = None,
) -> str:
    """
    Schedule a cron job on the job queue.

    Args:
        job_queue: Telegram JobQueue instance
        chat_id: Chat ID to send reminders to
        message: Reminder message
        cron_expression: 6-field cron string (second minute hour day month day_of_week)
        timezone_str: Timezone for the schedule
        start_datetime: Optional start time for the schedule
        end_datetime: Optional end time for the schedule

    Returns:
        Confirmation message with schedule details
    """
    from apscheduler.triggers.cron import CronTrigger

    # Parse cron expression
    parts = cron_expression.split()
    if len(parts) != 6:
        return "❌ Invalid cron expression. Must have exactly 6 fields: second minute hour day month day_of_week"

    second, minute, hour, day, month, day_of_week = parts

    # Set timezone
    tz = ZoneInfo(timezone_str)

    # Create trigger with all parameters
    trigger = CronTrigger(
        second=second,
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        start_date=start_datetime,
        end_date=end_datetime,
        timezone=tz,
    )

    job_id = f"reminder_{chat_id}_{cron_expression.replace(' ', '_')}"
    job_queue.run_custom(
        callback=reminder_callback,
        job_kwargs={
            "trigger": trigger,
            "id": job_id,
            "replace_existing": True,
        },
        name=job_id,
        chat_id=chat_id,
        data={"message": message},
    )

    # Build confirmation message
    details = "✅ Recurring reminder scheduled:\n"
    details += f"📝 Message: '{message}'\n"
    details += f"⏱️ Schedule: {cron_expression}\n"
    details += f"🌍 Timezone: {timezone_str}\n"
    if start_datetime:
        details += f"▶️ Starts: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n"
    else:
        details += "▶️ Starts: Immediately\n"
    if end_datetime:
        details += f"⏹️ Ends: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n"
    else:
        details += "⏹️ Ends: Never (runs indefinitely)\n"

    return details


def _list_reminders(job_queue: JobQueue, chat_id: int) -> list[str]:
    """
    List all reminders for a specific chat_id.

    Args:
        job_queue: Telegram JobQueue instance
        chat_id: Chat ID to filter reminders by

    Returns:
        List of strings describing each reminder
    """
    reminders = []

    # Use regex pattern to filter jobs by chat_id in the job name
    pattern = f"^reminder_{chat_id}_"
    jobs = job_queue.jobs(pattern=pattern)

    for job in jobs:
        message = job.data.get("message", "N/A")
        reminders.append(f"{message}")

    return reminders


def _delete_reminder(job_queue: JobQueue, chat_id: int, cron_expression: str) -> str:
    """
    Delete a specific reminder by its cron expression.

    Args:
        job_queue: Telegram JobQueue instance
        chat_id: Chat ID of the reminder owner
        cron_expression: The cron expression that identifies the reminder

    Returns:
        Confirmation message indicating success or failure
    """
    # Build the job ID using the same pattern as when scheduling
    job_id = f"reminder_{chat_id}_{cron_expression.replace(' ', '_')}"

    # Get the scheduler and try to remove the job
    scheduler = job_queue.scheduler
    job = scheduler.get_job(job_id)

    if job:
        job.remove()
        return f"✅ Reminder deleted successfully (ID: {job_id})"
    else:
        return "❌ No reminder found with the specified schedule"


async def reminder_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    JobQueue callback for sending reminders.

    This function is called by the Telegram JobQueue when a reminder is due.
    It accesses the message and chat_id from the job's context.

    Args:
        context: Telegram context containing job data and bot instance
    """
    job = context.job
    message = job.data["message"]
    chat_id = job.chat_id

    logger.info(f"⏰ REMINDER TRIGGERED for chat_id={chat_id}: {message}")
    formatted_message = f"🔔 Reminder: {message}"

    try:
        await context.bot.send_message(chat_id=chat_id, text=formatted_message)
        logger.info("✅ Reminder sent successfully")
    except Exception as e:
        logger.info(f"❌ Error sending reminder: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""

    orchestrator_agent = PydanticAgent(
        "openai:gpt-5-mini", system_prompt=get_agent_system_prompt()
    )

    @orchestrator_agent.tool
    def schedule_reminder(
        ctx: RunContext,
        message: str,
        cron_expression: str,
        start_datetime: datetime.datetime | None = None,
        end_datetime: datetime.datetime | None = None,
        timezone_str: str = "Europe/Brussels",
    ) -> str:
        """
        Schedule a recurring reminder using a cron expression with optional start/end times.

        Args:
            message: The reminder message to send to the user

            cron_expression: 6-field cron string that defines when the reminder repeats.
                Format: "second minute hour day month day_of_week"

                Examples:
                - "*/10 * * * * *" = Every 10 seconds (fires at 0, 10, 20, 30, 40, 50 seconds)
                - "0 */5 * * * *" = Every 5 minutes (fires at minute 0, 5, 10, 15, etc.)
                - "0 0 9 * * *" = Every day at 9:00 AM
                - "0 30 14 * * 1-5" = Every weekday (Mon-Fri) at 2:30 PM
                - "0 0 * * * *" = Every hour on the hour

                Field descriptions:
                - second: 0-59 or */N for every N seconds
                - minute: 0-59 or */N for every N minutes
                - hour: 0-23 or */N for every N hours
                - day: 1-31 (day of month)
                - month: 1-12 or jan,feb,mar,...
                - day_of_week: 0-6 (0=Monday) or mon,tue,wed,thu,fri,sat,sun

                Use "*" to match any value for that field.
                Use "*/N" to match every Nth value (e.g., */10 for every 10 seconds).

            start_datetime: Optional. When to start executing this cron schedule.
                If not provided, starts immediately.
                Use this to delay the start of a recurring reminder.
                Example: datetime(2025, 1, 1, 9, 0) starts on Jan 1, 2025 at 9:00 AM

            end_datetime: Optional. When to stop executing this cron schedule.
                If not provided, runs indefinitely until manually cancelled.
                Use this to automatically stop a recurring reminder after a certain time.
                Example: datetime.now() + timedelta(hours=1) stops after 1 hour

            timezone_str: Timezone for the schedule (default: "Europe/Brussels").
                Examples: "America/New_York", "Asia/Tokyo", "UTC"
                The cron times are interpreted in this timezone.

        Returns:
            Confirmation message with schedule details

        Usage examples:
        - Remind every 30 seconds for the next 5 minutes:
          schedule_repeat_reminder(
              message="Check your email",
              cron_expression="*/30 * * * * *",
              end_datetime=datetime.now() + timedelta(minutes=5)
          )

        - Remind every weekday at 9 AM starting next Monday:
          schedule_repeat_reminder(
              message="Daily standup",
              cron_expression="0 0 9 * * 1-5",
              start_datetime=datetime(2025, 1, 6, 9, 0)  # Next Monday
          )
        """
        details = _schedule_cron_job(
            job_queue=context.job_queue,
            chat_id=update.effective_chat.id,
            message=message,
            cron_expression=cron_expression,
            timezone_str=timezone_str,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
        )
        logger.info(details)
        return details

    @orchestrator_agent.tool
    def list_reminders(ctx: RunContext) -> str:
        """
        List all scheduled reminders for the current user.

        This tool retrieves all active recurring reminders that have been scheduled
        for the current chat. Use this when the user asks to see their reminders,
        check what reminders they have, or wants to know what's scheduled.

        Returns:
            A formatted string listing all active reminders with their messages.
            If no reminders are found, returns a message indicating no reminders exist.

        Usage examples:
        - "What reminders do I have?"
        - "Show me my scheduled reminders"
        - "List all my reminders"
        """
        chat_id = update.effective_chat.id
        reminders = _list_reminders(context.job_queue, chat_id)

        if not reminders:
            return "You have no scheduled reminders."

        result = "📋 Your scheduled reminders:\n\n"
        for i, reminder in enumerate(reminders, 1):
            result += f"{i}. {reminder}\n"

        return result

    @orchestrator_agent.tool
    def delete_reminder(ctx: RunContext, cron_expression: str) -> str:
        """
        Delete a specific reminder by its cron expression.

        Use this tool when the user wants to remove or cancel a scheduled reminder.
        The reminder is identified by its cron expression (schedule pattern).

        Args:
            cron_expression: The 6-field cron expression that identifies the reminder to delete.
                This must match exactly the cron expression used when scheduling the reminder.
                Format: "second minute hour day month day_of_week"

                Examples:
                - "0 0 9 * * *" - Daily 9 AM reminder
                - "0 30 14 * * 1-5" - Weekday 2:30 PM reminder
                - "*/10 * * * * *" - Every 10 seconds reminder

        Returns:
            Confirmation message indicating whether the reminder was successfully deleted
            or if no matching reminder was found.

        Usage examples:
        - "Delete my 9 AM daily reminder"
        - "Cancel the reminder at 2:30 PM"
        - "Remove my morning standup reminder"

        Note: To help users identify which reminder to delete, use the list_reminders tool first
        to show them their active reminders and their schedules.
        """
        chat_id = update.effective_chat.id
        result = _delete_reminder(context.job_queue, chat_id, cron_expression)
        logger.info(f"Delete reminder result for chat_id={chat_id}: {result}")
        return result

    @orchestrator_agent.tool
    async def book_gym(ctx: RunContext, booking_constraints: str) -> str:
        """Book a personal training gym session. Only input we need is some indication of when to book te session.
        The rest is handled by the browser agent.

        Args:
            booking_constraints: Provide a guideline of when you would like to book the session. Can be broad or narrow.
        """
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        full_task = f"""
            
            ## Specific details for the gym session

            {booking_constraints}

            ## General steps to book a gym session

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
            run_browser_automation(update.effective_chat.id, context, full_task)
        )
        return "On it!"

    user = update.effective_user
    message_text = update.message.text
    logger.info(f"Received from {user.first_name} ({user.id}): {message_text}")

    # Check if browser is waiting for response
    if "browser_state" in context.user_data:
        state = context.user_data["browser_state"]
        if state.get("waiting_for_response"):
            # This is a response to browser agent's question
            logger.info(f"Forwarding response to browser: {message_text}")
            state["user_response"] = message_text
            state["response_event"].set()
            return

    # Load chat history for this user
    user_id = user.id
    chat_history = get_user_chat_history(user_id)
    # Update system prompt in history to ensure latest prompt is used
    chat_history = update_system_prompt_in_history(chat_history)

    # Use orchestrator agent to decide what to do
    logger.info("🤔 Orchestrator agent analyzing message...")
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
    return result


def create_application() -> Application:
    """Create and configure the Telegram bot application."""

    logger.info("Creating personal assistant bot application...")

    # Get timezone from environment
    TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Europe/Brussels"))

    # Create application with JobQueue
    application = Application.builder().token(TOKEN).concurrent_updates(False).build()

    # Configure PTB-aware SQLite jobstore for persistence with timezone
    jobstore = PTBSQLiteJobStore(application=application, url=f"sqlite:///{DB_PATH}")
    job_queue = application.job_queue
    job_queue.scheduler.add_jobstore(jobstore, alias="default")
    logger.info(
        f"✅ PTB JobStore configured with SQLite ({DB_PATH}) and timezone {TIMEZONE}"
    )

    # Add message handler
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    return application


def main() -> None:
    """Start the bot."""
    application = create_application()
    # Run the bot
    logger.info("Bot is running! You can now book gym sessions or schedule reminders.")
    logger.info("JobQueue with APScheduler + SQLite persistence is active.")
    logger.info("Press Ctrl-C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
