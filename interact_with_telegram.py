#!/usr/bin/env python3
"""
Telegram bot with APScheduler integration for task scheduling.
"""
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
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
    jobstores = {
        'default': SQLAlchemyJobStore(url=db_url)
    }

    scheduler = AsyncIOScheduler(jobstores=jobstores)

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
