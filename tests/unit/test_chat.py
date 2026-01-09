#!/usr/bin/env python3
"""Test chat history persistence with sqlitedict."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_core import to_jsonable_python
from sqlitedict import SqliteDict


def test_user_chat_history_persistence():
    """Test that user data and chat history are correctly stored and retrieved as JSON."""
    # Setup: Create temp database
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_users.db"

        # Patch the chat module's user_db to use our test database
        with patch(
            "personal_assistant.chat.user_db", SqliteDict(str(db_path), autocommit=True)
        ):
            # Import functions after patching
            from personal_assistant.chat import (
                get_user_chat_history,
                save_user_chat_history,
            )

            # Simulate a Telegram user
            user_id = 12345
            user_data = {
                "id": user_id,
                "first_name": "Vincent",
                "last_name": "Claes",
                "username": "vincentclaes",
            }

            # Test 1: New user should have empty history
            chat_history = get_user_chat_history(user_id)
            assert chat_history == [], "New user should have empty chat history"

            # Test 2: Create mock messages and save them
            mock_messages = [
                ModelRequest(parts=[UserPromptPart(content="Hello")]),
                ModelResponse(parts=[TextPart(content="Hi there!")]),
            ]

            save_user_chat_history(user_id, user_data, mock_messages)

            # Test 3: Retrieve and verify messages are correctly deserialized
            retrieved_history = get_user_chat_history(user_id)
            assert len(retrieved_history) == 2, (
                f"Should have 2 messages, got {len(retrieved_history)}"
            )
            assert isinstance(retrieved_history[0], ModelRequest), (
                "First message should be ModelRequest"
            )
            assert isinstance(retrieved_history[1], ModelResponse), (
                "Second message should be ModelResponse"
            )

            # Test 4: Update with more messages
            updated_messages = mock_messages + [
                ModelRequest(parts=[UserPromptPart(content="What's 2+2?")]),
                ModelResponse(parts=[TextPart(content="4")]),
            ]

            save_user_chat_history(user_id, user_data, updated_messages)

            # Test 5: Verify all messages persisted
            final_history = get_user_chat_history(user_id)
            assert len(final_history) == 4, (
                f"Should have 4 messages, got {len(final_history)}"
            )

            # Test 6: Verify JSON serialization/deserialization works correctly
            # Convert to JSON and back
            messages_json = to_jsonable_python(final_history)
            restored_messages = ModelMessagesTypeAdapter.validate_python(messages_json)
            assert len(restored_messages) == 4, (
                "Messages should survive JSON round-trip"
            )

        print(
            "✅ Test passed: User data and chat history JSON persistence works correctly"
        )


def test_system_prompt_update():
    """Test that system prompt is correctly updated or added in chat history."""
    from personal_assistant.chat import update_system_prompt_in_history

    # Test 1: Replace existing system prompt
    messages_with_prompt = [
        ModelRequest(
            parts=[
                SystemPromptPart(content="Old system prompt"),
                UserPromptPart(content="Hello"),
            ]
        ),
        ModelResponse(parts=[TextPart(content="Hi there!")]),
    ]

    # Mock get_agent_system_prompt function
    with patch(
        "personal_assistant.chat.get_agent_system_prompt",
        return_value="New system prompt",
    ):
        updated = update_system_prompt_in_history(messages_with_prompt)

    assert len(updated) == 2, "Should have same number of messages"
    assert isinstance(updated[0].parts[0], SystemPromptPart), (
        "First part should be SystemPromptPart"
    )
    assert updated[0].parts[0].content == "New system prompt", (
        "System prompt should be replaced"
    )

    # Test 2: Add system prompt when missing
    messages_without_prompt = [
        ModelRequest(parts=[UserPromptPart(content="Hello")]),
        ModelResponse(parts=[TextPart(content="Hi there!")]),
    ]

    with patch(
        "personal_assistant.chat.get_agent_system_prompt",
        return_value="New system prompt",
    ):
        updated = update_system_prompt_in_history(messages_without_prompt)

    assert len(updated) == 2, "Should have same number of messages"
    assert isinstance(updated[0].parts[0], SystemPromptPart), (
        "First part should be SystemPromptPart"
    )
    assert updated[0].parts[0].content == "New system prompt", (
        "System prompt should be added"
    )

    # Test 3: Empty history returns empty
    empty_history = []
    updated = update_system_prompt_in_history(empty_history)
    assert updated == [], "Empty history should remain empty"

    print("✅ Test passed: System prompt update works correctly")


if __name__ == "__main__":
    test_user_chat_history_persistence()
    test_system_prompt_update()
