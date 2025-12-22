#!/usr/bin/env python3
"""
Minimal example: Telegram bot that can trigger browser automation with user interaction.

Flow:
1. User sends message to bot
2. If message contains "book gym", trigger browser automation
3. Browser agent asks questions via Telegram
4. User responds in same conversation
5. Browser completes and reports back
"""
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

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_API_KEY')

if not TOKEN:
    raise ValueError("TELEGRAM_API_KEY not found in .env file")


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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
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

    # Check if user wants browser automation
    if 'browse' in message_text.lower() or 'book' in message_text.lower():
        # Simple task for testing
        task = """
        Go to https://example.com
        Then use the ask_user action to ask me: "What website should I visit next?"
        Wait for my response and navigate to that website.
        Then use ask_user again to ask: "Should I take a screenshot? (yes/no)"
        If yes, describe what you see on the page.
        """

        # Run browser automation as background task (non-blocking)
        context.application.create_task(
            run_browser_automation(update.effective_chat.id, context, task)
        )
    else:
        # Normal conversation
        await update.message.reply_text(
            f"You said: {message_text}\n\n"
            f"Try saying 'browse' or 'book' to trigger browser automation!"
        )


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
