# Calendar Event Tool Design

## Overview

Add a `create_calendar_event` tool to the orchestrator agent that generates an .ics file and sends it to the user via Telegram as a file attachment.

## User Experience

User says something like:

- "Create a meeting tomorrow at 3pm called Team Sync"
- "Add dentist appointment on January 20th at 10:30"
- "Schedule a 30 min call with John on Friday at 2pm"

Bot responds with an .ics file attachment that the user can tap to add to their calendar.

## Defaults

| Field    | Default                                   |
| -------- | ----------------------------------------- |
| Duration | 1 hour (overridable via natural language) |
| Alerts   | 1 hour before, 10 minutes before          |
| Timezone | Europe/Brussels                           |

## Technical Approach

### New Tool Function

Add `create_calendar_event` as a tool on the orchestrator agent in `app.py`:

```python
@orchestrator_agent.tool
async def create_calendar_event(
    ctx: RunContext,
    title: str,
    start_datetime: datetime.datetime,
    duration_minutes: int = 60,
) -> str:
```

The AI extracts title, start time, and optional duration from natural language. The tool:

1. Generates an .ics file with the event + alerts
2. Sends it via Telegram as a document attachment
3. Returns a confirmation message

### .ics Generation

Use the `icalendar` library to build the VEVENT with:

- DTSTART / DTEND based on start_datetime and duration
- Two VALARM components (60 min and 10 min before)
- SUMMARY from title
- Auto-generated UID

### File Delivery

Write .ics content to a temporary file, send via `context.bot.send_document()`, then clean up.

## Test Strategy

### Integration test (`tests/integration/test_handle_message.py`)

- Mock the `create_calendar_event` tool (like existing tests mock other tools)
- Verify the agent calls the tool with correct parameters when user asks to create an event

### Unit test (`tests/unit/test_calendar.py`)

- Test the .ics generation function directly
- Verify it produces valid .ics content with correct title, times, and alerts
- No AI interaction — pure function test

## Dependencies

Add `icalendar` package:

```bash
uv add icalendar
```
