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
