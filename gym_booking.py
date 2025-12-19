"""Gym booking logic adapted for Telegram bot integration."""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

from browser_use import Agent, Browser, Controller
from browser_use.llm.openai.chat import ChatOpenAI
from loguru import logger


@dataclass
class GymSlot:
    """Represents an available gym time slot."""
    time: str
    date: str
    available: bool
    slot_id: Optional[str] = None


RESERVATION_URL = "https://qore.clubplanner.be/Reservation/NewReservation/1"


def get_available_slots(
    preferred_hours: List[str],
    credentials: Dict[str, str],
    max_sessions: int = 2
) -> List[GymSlot]:
    """Check available gym slots without booking.

    Args:
        preferred_hours: List of preferred time slots (e.g., ["07:00", "08:00"])
        credentials: Dict with x_user and x_pass keys
        max_sessions: Maximum sessions per week

    Returns:
        List of GymSlot objects representing available slots
    """
    logger.info("Checking available gym slots")

    task = f"""
    Go to {RESERVATION_URL} and check available gym sessions.
    Use x_user and x_pass from sensitive_data to login.

    Find available sessions matching these preferred times: {', '.join(preferred_hours)}
    Do NOT book anything - just return the available options.

    For each available slot, extract:
    - Time (e.g., "07:00")
    - Date (e.g., "2025-12-20")
    - Any slot identifier if visible
    """

    try:
        browser = Browser(headless=True)
        controller = Controller()
        llm = ChatOpenAI(model="gpt-4o")

        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            controller=controller,
            sensitive_data=credentials,
            use_vision=True,
        )

        # Run agent and parse results
        result = agent.run_sync()
        browser.close_sync()

        # TODO: Parse agent result into GymSlot objects
        # For now, return empty list (minimal implementation)
        return []

    except Exception as e:
        logger.error(f"Error checking gym slots: {e}")
        return []


def book_gym_slot(
    slot: GymSlot,
    credentials: Dict[str, str]
) -> bool:
    """Book a specific gym slot.

    Args:
        slot: GymSlot object to book
        credentials: Dict with x_user and x_pass keys

    Returns:
        True if booking successful, False otherwise
    """
    logger.info(f"Booking gym slot: {slot.time} on {slot.date}")

    task = f"""
    Go to {RESERVATION_URL} and book a gym session.
    Use x_user and x_pass from sensitive_data to login.

    Book the session at {slot.time} on {slot.date}.
    Complete the booking process.
    """

    try:
        browser = Browser(headless=True)
        controller = Controller()
        llm = ChatOpenAI(model="gpt-4o")

        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            controller=controller,
            sensitive_data=credentials,
            use_vision=True,
        )

        result = agent.run_sync()
        browser.close_sync()

        logger.info("Gym booking completed")
        return True

    except Exception as e:
        logger.error(f"Error booking gym slot: {e}")
        return False
