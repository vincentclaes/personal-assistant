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
