# Calendar Event Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a tool that creates .ics calendar files and sends them via Telegram.

**Architecture:** Extract .ics generation into a pure function in a new `calendar.py` module. The orchestrator tool calls this function, writes to a temp file, sends via Telegram, and cleans up.

**Tech Stack:** icalendar library, python-telegram-bot, tempfile

---

## Task 1: Add icalendar dependency

**Step 1: Install the package**

Run: `uv add icalendar`

**Step 2: Verify installation**

Run: `uv run python -c "from icalendar import Calendar; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add icalendar dependency"
```

---

## Task 2: Unit test for .ics generation

**Files:**

- Create: `tests/unit/test_calendar.py`
- Create: `personal_assistant/calendar.py`

**Step 1: Write the failing test**

Create `tests/unit/test_calendar.py`:

```python
#!/usr/bin/env python3
"""Test calendar .ics file generation."""

import datetime
from zoneinfo import ZoneInfo


def test_generate_ics_creates_valid_ics_content():
    """Test that generate_ics produces valid .ics content with title, times, and alerts."""
    from personal_assistant.calendar import generate_ics

    title = "Team Sync"
    start = datetime.datetime(2026, 1, 15, 15, 0, tzinfo=ZoneInfo("Europe/Brussels"))
    duration_minutes = 60

    ics_content = generate_ics(title, start, duration_minutes)

    # Verify it's valid ics content
    assert ics_content.startswith(b"BEGIN:VCALENDAR")
    assert b"END:VCALENDAR" in ics_content

    # Verify event details
    assert b"SUMMARY:Team Sync" in ics_content
    assert b"BEGIN:VEVENT" in ics_content
    assert b"END:VEVENT" in ics_content

    # Verify alerts (VALARM components)
    assert ics_content.count(b"BEGIN:VALARM") == 2
    assert b"TRIGGER:-PT1H" in ics_content  # 1 hour before
    assert b"TRIGGER:-PT10M" in ics_content  # 10 minutes before
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/unit/test_calendar.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'personal_assistant.calendar'`

**Step 3: Write minimal implementation**

Create `personal_assistant/calendar.py`:

```python
#!/usr/bin/env python3
"""Calendar .ics file generation."""

import datetime
import uuid

from icalendar import Alarm, Calendar, Event


def generate_ics(
    title: str,
    start: datetime.datetime,
    duration_minutes: int = 60,
) -> bytes:
    """
    Generate .ics calendar file content.

    Args:
        title: Event title/summary
        start: Event start datetime (must be timezone-aware)
        duration_minutes: Event duration in minutes (default: 60)

    Returns:
        .ics file content as bytes
    """
    cal = Calendar()
    cal.add("prodid", "-//Personal Assistant//EN")
    cal.add("version", "2.0")

    event = Event()
    event.add("uid", str(uuid.uuid4()))
    event.add("summary", title)
    event.add("dtstart", start)
    event.add("dtend", start + datetime.timedelta(minutes=duration_minutes))
    event.add("dtstamp", datetime.datetime.now(datetime.UTC))

    # Alert 1 hour before
    alarm_1h = Alarm()
    alarm_1h.add("action", "DISPLAY")
    alarm_1h.add("trigger", datetime.timedelta(hours=-1))
    alarm_1h.add("description", title)
    event.add_component(alarm_1h)

    # Alert 10 minutes before
    alarm_10m = Alarm()
    alarm_10m.add("action", "DISPLAY")
    alarm_10m.add("trigger", datetime.timedelta(minutes=-10))
    alarm_10m.add("description", title)
    event.add_component(alarm_10m)

    cal.add_component(event)

    return cal.to_ical()
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/unit/test_calendar.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add personal_assistant/calendar.py tests/unit/test_calendar.py
git commit -m "feat: add calendar .ics generation with alerts"
```

---

## Task 3: Integration test for create_calendar_event tool

**Files:**

- Modify: `tests/integration/test_handle_message.py`

**Step 1: Write the failing test**

Add to `tests/integration/test_handle_message.py`:

```python
@pytest.mark.asyncio
async def test_handle_message_create_calendar_event(mock_user_db):
    """Test that 'create calendar event' calls calendar.generate_ics and sends document."""
    with patch("personal_assistant.calendar.generate_ics") as mock_generate:
        mock_generate.return_value = b"BEGIN:VCALENDAR\nEND:VCALENDAR"

        mock_update = create_mock_update(
            chat_id=123, message_text="create a meeting called Team Sync tomorrow at 3pm"
        )
        mock_context = create_mock_context()
        mock_context.bot = AsyncMock()
        mock_context.bot.send_document = AsyncMock()

        response = await handle_message(mock_update, mock_context)

        mock_generate.assert_called_once()
        # Verify title was passed
        call_args = mock_generate.call_args
        assert call_args[0][0] == "Team Sync"  # title
        # Verify document was sent
        mock_context.bot.send_document.assert_called_once()
        assert isinstance(response, AgentRunResult)
```

**Step 2: Run test to verify it fails**

Run: `uv run python -m pytest tests/integration/test_handle_message.py::test_handle_message_create_calendar_event -v`
Expected: FAIL (tool doesn't exist yet)

**Step 3: Implement the tool**

Add to `personal_assistant/app.py` inside `orchestrator_agent_init()`, after the other tool definitions:

First, add import at top of file:

```python
from personal_assistant import calendar
```

Then add the tool inside `orchestrator_agent_init()`:

```python
    @orchestrator_agent.tool
    async def create_calendar_event(
        ctx: RunContext,
        title: str,
        start_datetime: datetime.datetime,
        duration_minutes: int = 60,
    ) -> str:
        """
        Create a calendar event and send it as an .ics file via Telegram.

        Use this when the user wants to create a calendar event, meeting, or appointment.
        The .ics file can be opened to add the event to any calendar app.

        Args:
            title: The event title/name (e.g., "Team Sync", "Dentist appointment")
            start_datetime: When the event starts (timezone-aware datetime)
            duration_minutes: Event duration in minutes (default: 60)

        Returns:
            Confirmation message that the calendar event was created and sent
        """
        import tempfile
        from pathlib import Path

        # Generate .ics content
        ics_content = calendar.generate_ics(title, start_datetime, duration_minutes)

        # Write to temp file and send via Telegram
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".ics", delete=False
        ) as tmp_file:
            tmp_file.write(ics_content)
            tmp_path = Path(tmp_file.name)

        try:
            # Create a safe filename from the title
            safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
            safe_title = safe_title.replace(" ", "_")[:50]
            filename = f"{safe_title}.ics"

            with open(tmp_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=f,
                    filename=filename,
                )
        finally:
            tmp_path.unlink()  # Clean up temp file

        return f"Calendar event '{title}' created and sent."
```

**Step 4: Run test to verify it passes**

Run: `uv run python -m pytest tests/integration/test_handle_message.py::test_handle_message_create_calendar_event -v`
Expected: PASS

**Step 5: Run all tests to ensure no regressions**

Run: `uv run python -m pytest -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add personal_assistant/app.py tests/integration/test_handle_message.py
git commit -m "feat: add create_calendar_event tool to orchestrator"
```

---

## Task 4: Manual verification

**Step 1: Start the bot locally**

Run: `uv run python -m personal_assistant.app`

**Step 2: Test via Telegram**

Send message: "Create a meeting called Test Event tomorrow at 2pm"

Expected: Bot sends an .ics file attachment

**Step 3: Verify .ics file**

- Download the file
- Open it in a calendar app
- Verify: title, time, and two alerts (1 hour and 10 min before)
