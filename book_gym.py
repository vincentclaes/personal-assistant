import os

from browser_use import Agent, Browser, Controller
from browser_use.agent.views import ActionResult
from browser_use.llm.openai.chat import ChatOpenAI
from loguru import logger

sensitive_data = {"x_user": "vincent.v.claes@gmail.com", "x_pass": os.getenv("QORE_PASSWORD")}

RESERVATION_URL = "https://qore.clubplanner.be/Reservation/NewReservation/1"

PREFERRED_HOURS = ["07:00", "08:00", "12:00", "16:00"]
MAX_SESSIONS_PER_WEEK = 2

TASK = f"""
Go to {RESERVATION_URL} and help me book a gym session.
use x_user and x_pass to login, just fill in the values of sensitive_data x_user is the key for username and x_pass is the key for password.

My preferences:
1. Preferred time slots (in order of priority): {', '.join(PREFERRED_HOURS)}
2. On Saturdays, any time slot is fine
3. Maximum {MAX_SESSIONS_PER_WEEK} sessions per week

Steps:
1. Navigate to the reservation page
2. Look at the available sessions/time slots
3. Find sessions matching my preferred times (or any Saturday slot)
4. IMPORTANT: Use the ask_user tool to present the available sessions that match my preferences and get confirmation on which one to book
5. Only after receiving confirmation via ask_user, proceed with the booking

Do NOT book anything without explicit confirmation using the ask_user tool.
"""


def create_custom_controller():
    """Create a controller with custom user interaction tool."""
    controller = Controller()

    # Add custom tool for asking user for input
    @controller.registry.action(
        'Ask the user a question and wait for their response. Use this when you need user input or confirmation.',
    )
    def ask_user(question: str) -> ActionResult:
        """
        Ask the user a question and wait for their answer.

        Args:
            question: The question to ask the user

        Returns:
            ActionResult with the user's response
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"AGENT QUESTION: {question}")
        logger.info(f"{'='*60}\n")

        try:
            # Get input from user
            user_response = input("Your response: ").strip()

            logger.info(f"\nUser responded: {user_response}\n")

            memory = f"Asked user: '{question}'. User responded: '{user_response}'"
            return ActionResult(
                extracted_content=user_response,
                long_term_memory=memory
            )
        except (KeyboardInterrupt, EOFError):
            error_msg = "User cancelled input"
            logger.warning(error_msg)
            return ActionResult(error=error_msg)

    return controller


def main():
    logger.info("Starting gym booking agent")

    # Create browser and controller with custom tools
    browser = Browser(headless=False)
    controller = create_custom_controller()
    llm = ChatOpenAI(model="gpt-4o")

    agent = Agent(
        task=TASK,
        llm=llm,
        browser=browser,
        controller=controller,
        sensitive_data=sensitive_data,
        use_vision=True,
    )

    logger.info(f"Navigating to {RESERVATION_URL}")
    agent.run_sync()
    logger.info("Agent finished")
    browser.close_sync()


if __name__ == "__main__":
    main()
