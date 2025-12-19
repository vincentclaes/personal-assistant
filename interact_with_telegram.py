#!/usr/bin/env python3
"""
Telegram bot that responds to messages with 'hello there!'
"""
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()

# Get the bot token from environment variable
TOKEN = os.getenv('TELEGRAM_API_KEY')

if not TOKEN:
    raise ValueError("TELEGRAM_API_KEY not found in .env file. Please add your bot token.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text('Bot is now active! Send me any message and I will respond.')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages and respond with 'hello there!'"""
    # Log the received message
    user = update.effective_user
    message_text = update.message.text
    print(f"Received message from {user.first_name} (@{user.username}): {message_text}")

    # Respond with "hello there!"
    await update.message.reply_text('hello there!')


def main() -> None:
    """Start the bot."""
    print("Starting bot...")

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot until the user presses Ctrl-C
    print(f"Bot is running! Send messages to @sidekick_pa_bot on Telegram.")
    print("Press Ctrl-C to stop the bot.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
