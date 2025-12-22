#!/usr/bin/env python3
"""
Telegram bot that responds to messages with 'hello there!'
"""
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Load environment variables
load_dotenv()

# Get the bot token from environment variable
TOKEN = os.getenv('TELEGRAM_API_KEY')

if not TOKEN:
    raise ValueError("TELEGRAM_API_KEY not found in .env file. Please add your bot token.")

# Define conversation state
CONVERSATION = 0


async def handle_conversation_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle messages in the conversation and check for 'foo' to end."""
    user = update.effective_user
    message_text = update.message.text
    print(f"Received message from {user.first_name} (@{user.username}): {message_text}")

    # Initialize conversation history if it doesn't exist
    if 'conversation_history' not in context.user_data:
        context.user_data['conversation_history'] = []

    # Add message to conversation history
    context.user_data['conversation_history'].append({
        'user': user.first_name,
        'message': message_text,
        'timestamp': update.message.date
    })

    # Check if message contains 'foo'
    if 'foo' in message_text.lower():
        # Print conversation history before ending
        history = context.user_data['conversation_history']
        print(f"\n=== Conversation History ({len(history)} messages) ===")
        for i, msg in enumerate(history, 1):
            print(f"{i}. [{msg['timestamp']}] {msg['user']}: {msg['message']}")
        print("=== End of Conversation ===\n")

        await update.message.reply_text("Found 'foo'! Ending this conversation.")

        # Clear history for next conversation
        context.user_data = {}
        return ConversationHandler.END

    # Continue conversation
    message_count = len(context.user_data['conversation_history'])
    await update.message.reply_text(
        f"You said: {message_text}\n"
        f"Messages in this conversation: {message_count}\n"
        f"Say 'foo' to end!"
    )
    return CONVERSATION


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text("Conversation cancelled. Use /start to begin again.")
    return ConversationHandler.END


def main() -> None:
    """Start the bot."""
    print("Starting bot...")

    # Create the Application
    # Disable concurrent_updates as required by ConversationHandler
    application = Application.builder().token(TOKEN).concurrent_updates(False).build()

    # Setup ConversationHandler
    # Entry point accepts any text message to start a conversation
    # When conversation ends (on 'foo'), next message automatically starts a new one
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_conversation_message)],
        states={
            CONVERSATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_conversation_message)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Register handlers
    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    print(f"Bot is running! Send messages to @sidekick_pa_bot on Telegram.")
    print("Press Ctrl-C to stop the bot.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
