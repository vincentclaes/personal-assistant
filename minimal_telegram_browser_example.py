#!/usr/bin/env python3

import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
)
from browser_use import Agent, Browser, Controller
from browser_use.agent.views import ActionResult
from browser_use.llm.openai.chat import ChatOpenAI
from pydantic_ai import Agent as PydanticAgent, RunContext

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_API_KEY')

if not TOKEN:
    raise ValueError("TELEGRAM_API_KEY not found in .env file")


# Create orchestrator agent (no deps needed for simple tools)
orchestrator_agent = PydanticAgent(
    'openai:gpt-4o-mini',
    system_prompt="""You are a personal assistant bot that helps users with tasks like:
- Booking gym sessions (requires browser automation)
- General questions and conversation
- Creating reminders (future feature)
"""
)

def create_telegram_aware_controller(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    """
    Create a Controller with actions that can interact via Telegram.

    Args:
        chat_id: Telegram chat ID to send messages to
        context: Telegram Context object for conversation state
    """
    controller = Controller()

    # Store pending question and response in context
    if 'browser_state' not in context.user_data:
        context.user_data['browser_state'] = {
            'waiting_for_response': False,
            'pending_question': None,
            'user_response': None,
            'response_event': asyncio.Event()
        }

    @controller.registry.action('Ask the user a question via Telegram and wait for their response')
    async def ask_user(question: str) -> ActionResult:
        """
        Ask user a question via Telegram and wait for response.

        Args:
            question: The question to ask the user

        Returns:
            ActionResult with the user's response
        """
        state = context.user_data['browser_state']

        # Send question to Telegram using bot
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🤖 Browser Agent asks:\n\n{question}\n\n(Reply with your answer)"
        )

        # Mark that we're waiting for response
        state['waiting_for_response'] = True
        state['pending_question'] = question
        state['user_response'] = None
        state['response_event'].clear()

        # Wait for user to respond
        await state['response_event'].wait()


        # Get the response
        user_response = state['user_response']
        state['waiting_for_response'] = False
        state['pending_question'] = None

        memory = f"Asked user: '{question}'. User responded: '{user_response}'"
        return ActionResult(
            extracted_content=user_response,
            long_term_memory=memory
        )

    @controller.registry.action('Send the user a final update via Telegram before ending the session')
    async def send_final_update(message: str) -> ActionResult:
        """
        Send a final informational message to the user via Telegram (no response needed). 
        Typically when a session is booked, nothing is available or an error occurred.

        Args:
            message: The message to send to the user

        Returns:
            ActionResult confirming the message was sent
        """
        text = f"🤖 Browser Agent final update:\n\n{message}"
        await context.bot.send_message(
            chat_id=chat_id,
            text=text
        )

        return ActionResult(
                is_done=True,
                success=False,
                long_term_memory=text
        )

    return controller

async def run_browser_automation(chat_id: int, context: ContextTypes.DEFAULT_TYPE, task: str):
    """
    Run browser automation with Telegram integration.

    Args:
        chat_id: Telegram chat ID to send messages to
        context: Telegram Context object
        task: Task description for browser agent
    """
    await context.bot.send_message(chat_id=chat_id, text="🌐 Starting browser automation...")

    # Create browser and controller
    browser = Browser(headless=False)
    controller = create_telegram_aware_controller(chat_id, context)
    llm = ChatOpenAI(model="gpt-4o")

    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        controller=controller,
        use_vision=True,
        sensitive_data= {"x_user": "vincent.v.claes@gmail.com", "x_pass": os.getenv("QORE_PASSWORD")}

    )

    try:
        # Run the agent (async)
        result = await agent.run()
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Browser automation completed!\n\nSteps taken: {len(result.history)}"
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Error during automation: {e}"
        )
    finally:
        await browser.close()

LAUNCH_SIGNAL = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
    global LAUNCH_SIGNAL
    if LAUNCH_SIGNAL:
        @orchestrator_agent.tool
        async def dispatch_browser(ctx: RunContext, task_description: str) -> str:
            """Trigger browser automation for tasks like booking gym, browsing websites, etc.

            Args:
                task_description: Clear description of what the browser should do
            """

            task_description = f"""
            Go to https://qore.clubplanner.be/ and login with x_user and x_pass to login, 
            just fill in the values of sensitive_data x_user is the key for username and x_pass is the key for password.

            Steps:
            1. go to https://qore.clubplanner.be/Reservation/NewReservation/1 
            2. Read carefully the selected date and the available sessions.
            3. List the sessions with date / time / name of the session / amount of available spots.
            4. IF there is at least an available spot, show the user the "date / time / name of the session / amount of available spots" for each available spot.
            6. Only after receiving confirmation via ask_user, proceed with the booking.
            7. you should receive a popup/confirmation message after booking, capture that and report back to me.
            8. double check the booking by navigating to 'My Reservations' page and confirm the session is listed there.
            9. Send a final_update message and the details of the booked session.
            10. ELSE IF there is no available spot, continue to the next date in the UI and repeat steps 2-4 until you find an available spot 
            11. IF you reach the end of the available dates, send a final_update message there are no spots available.

            Do NOT book anything without explicit confirmation using the ask_user tool.
            If the users cancel or do not confirm, do not proceed with booking and stop the process.
            """
            # Start browser automation in background so message handler stays free
            context.application.create_task(
                run_browser_automation(update.effective_chat.id, context, task_description)
            )
            return "Started browser automation in background"

        LAUNCH_SIGNAL = False
            

    user = update.effective_user
    message_text = update.message.text
    print(f"Received from {user.first_name}: {message_text}")

    # Check if browser is waiting for response
    if 'browser_state' in context.user_data:
        state = context.user_data['browser_state']
        if state.get('waiting_for_response'):
            # This is a response to browser agent's question
            print(f"Forwarding response to browser: {message_text}")
            state['user_response'] = message_text
            state['response_event'].set()
            return


    # Use orchestrator agent to decide what to do
    print("🤔 Orchestrator agent analyzing message...")
    result = await orchestrator_agent.run(message_text)

    # Extract the tool result (agent returns the last tool call result as output)
    output = result.output
    await update.message.reply_text(output)



def main() -> None:
    """Start the bot."""
    print("Starting minimal Telegram + browser_use example...")

    # Create application
    application = Application.builder().token(TOKEN).concurrent_updates(False).build()

    # Add message handler
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Run the bot
    print("Bot is running! Send 'browse' or 'book' to trigger browser automation.")
    print("Press Ctrl-C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
