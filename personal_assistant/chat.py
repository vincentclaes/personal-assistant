#!/usr/bin/env python3
"""Chat history and user management module."""

import datetime
from textwrap import dedent

from loguru import logger
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    SystemPromptPart,
)
from pydantic_core import to_jsonable_python
from sqlitedict import SqliteDict

from personal_assistant.database import DB_PATH


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
