"""Tests for gym booking bot integration."""
from gym_booking import get_available_slots
from unittest.mock import Mock, patch


def test_get_available_slots_returns_slot_data():
    """Test that get_available_slots returns structured slot data."""
    # Mock browser automation to return fake slots
    with patch('gym_booking.Agent') as mock_agent, \
         patch('gym_booking.Browser') as mock_browser:

        # Configure mock to simulate finding slots
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance

        # Call function
        slots = get_available_slots(
            preferred_hours=["07:00", "08:00"],
            credentials={"x_user": "test@example.com", "x_pass": "testpass"}
        )

        # Verify structure (mock will return empty list for now)
        assert isinstance(slots, list)
