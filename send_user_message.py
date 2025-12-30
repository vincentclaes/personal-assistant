#!/usr/bin/env python3
"""
Send a message to the Telegram bot programmatically.
The message triggers the bot's handlers exactly like a real user message.
"""
import os
import asyncio
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()
TOKEN = os.getenv('TELEGRAM_API_KEY')

if not TOKEN:
    raise ValueError("TELEGRAM_API_KEY not found in .env file")


async def send_user_message(chat_id: int, message_text: str) -> None:
    """
    Send a message to the bot that triggers handlers.

    Args:
        chat_id: Telegram user/chat ID
        message_text: The message text to send
    """
    bot = Bot(token=TOKEN)
    async with bot:
        await bot.send_message(chat_id=chat_id, text=message_text)


def send_message_sync(chat_id: int, message_text: str) -> None:
    """Synchronous wrapper for use in non-async contexts."""
    asyncio.run(send_user_message(chat_id, message_text))


if __name__ == '__main__':
    # Example usage
    import sys
    if len(sys.argv) != 3:
        print("Usage: python send_user_message.py <chat_id> <message>")
        sys.exit(1)

    chat_id = int(sys.argv[1])
    message = sys.argv[2]
    send_message_sync(chat_id, message)
    print(f"✅ Sent '{message}' to chat_id {chat_id}")
