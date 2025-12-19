#!/usr/bin/env python3
"""
Telegram bot with APScheduler integration and Pydantic AI agent for task scheduling.
"""
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from pydantic_ai import Agent
from loguru import logger

from task_store import TaskStore
from task_handlers import send_reminder_handler, gym_booking_handler
from agent_tools import create_schedule_tool, list_schedules_tool, cancel_schedule_tool

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
    jobstores = {
        'default': SQLAlchemyJobStore(url=db_url)
    }

    scheduler = AsyncIOScheduler(jobstores=jobstores)

    return scheduler


def create_agent(scheduler: AsyncIOScheduler, task_store: TaskStore) -> Agent:
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
    agent = Agent(
        'openai:gpt-4o',
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

Be conversational and helpful. Always confirm details before scheduling.""",
    )

    # Register tools with agent
    agent.tool(schedule_tool, name="create_schedule")
    agent.tool(list_tool, name="list_schedules")
    agent.tool(cancel_tool, name="cancel_schedule")

    return agent


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        'Personal Assistant Bot activated! 🤖\n\n'
        'I can help you:\n'
        '- Set reminders\n'
        '- Schedule gym bookings\n'
        '- List your schedules\n'
        '- Cancel schedules\n\n'
        'Just talk to me naturally!'
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages with Pydantic AI agent."""
    user = update.effective_user
    message_text = update.message.text
    logger.info(f"Received message from {user.first_name} (@{user.username}): {message_text}")

    # Get agent from context
    agent = context.bot_data.get('agent')
    if not agent:
        await update.message.reply_text("Agent not initialized. Please restart the bot.")
        return

    try:
        # Run agent with user message
        result = await agent.run(message_text)

        # Send agent's response
        response = result.data
        await update.message.reply_text(response)
        logger.info(f"Agent responded: {response}")

    except Exception as e:
        logger.error(f"Error processing message with agent: {e}")
        await update.message.reply_text(
            "Sorry, I encountered an error processing your request. "
            "Please try rephrasing or contact support."
        )


def main() -> None:
    """Start the bot."""
    logger.info("Starting bot with scheduler...")

    # Create scheduler
    scheduler = create_scheduler()

    # Create task store
    task_store = TaskStore()
    logger.info("Task store initialized")

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Create task handlers with bot reference
    bot = application.bot
    reminder_handler = send_reminder_handler(bot, task_store)
    gym_handler = gym_booking_handler(bot, task_store)

    # Register handlers with scheduler as regular functions
    scheduler.add_job(
        func=lambda job_id: reminder_handler(job_id),
        trigger='interval',
        seconds=3600,  # Placeholder, actual jobs will have their own triggers
        id='reminder_template',
        replace_existing=True
    )

    # Start scheduler (after handlers registered)
    scheduler.start()
    logger.info("Scheduler started")

    # Create Pydantic AI agent
    agent = create_agent(scheduler, task_store)
    logger.info("AI agent initialized")

    # Store dependencies in application context
    application.bot_data['scheduler'] = scheduler
    application.bot_data['task_store'] = task_store
    application.bot_data['agent'] = agent

    # Register Telegram handlers
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


if __name__ == '__main__':
    main()
