# Send User Message Module Design

## Overview

Create a standalone Python module (`send_user_message.py`) that programmatically sends messages to the Telegram bot, triggering the bot's handlers exactly as if a real user sent the message.

## Problem

Scheduled tasks (via `scheduler.py`) need to trigger bot actions programmatically. For example, a scheduled job should be able to send "book gym" to trigger the browser automation workflow.

## Solution

Use Telegram's Bot API directly to send messages. The message flows through Telegram's servers and comes back to the running bot via `run_polling()`, triggering `handle_message` normally.

**Key insight:** No IPC needed. Just use the same Telegram API that real clients use.

## Implementation

### Module: `send_user_message.py`

```python
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
```

### Usage Examples

**From command line:**
```bash
python send_user_message.py 123456789 "book gym"
```

**From scheduler:**
```python
from send_user_message import send_message_sync

def scheduled_gym_check():
    send_message_sync(chat_id=123456789, message_text="book gym")
```

**From async code:**
```python
from send_user_message import send_user_message

await send_user_message(chat_id=123456789, message_text="book gym")
```

## How It Works

1. `send_user_message.py` creates a Bot instance with the same token as `app.py`
2. Calls `bot.send_message(chat_id, text)` - sends message via Telegram API
3. Message goes to Telegram's servers
4. Running `app.py` polls Telegram and receives the message as an Update
5. `handle_message` processes it normally - no difference from real user message

## Testing

Create a simple test to verify the flow works end-to-end.

## Trade-offs

**Pros:**
- Dead simple - uses existing Telegram infrastructure
- No IPC complexity
- No new dependencies
- Works across any process boundaries
- Fail loudly - network/API errors propagate clearly

**Cons:**
- Requires network round-trip through Telegram's servers (adds ~100-500ms latency)
- User will see the message in their Telegram chat
- Requires bot token (already have it)

**Accepted trade-offs:**
- Network latency is acceptable for scheduled tasks
- User seeing automated messages is actually desirable for transparency
