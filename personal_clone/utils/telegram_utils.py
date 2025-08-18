import os
import telegram
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

def get_telegram_client():
    """Initializes and returns a Telegram client."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set.")
    return telegram.Bot(token=TELEGRAM_BOT_TOKEN)

async def get_chat_history(bot: telegram.Bot, chat_id: str, limit: int = 100):
    """Gets the chat history for a given chat ID."""
    updates = await bot.get_updates(offset=-limit, limit=limit)
    chat_updates = [u for u in updates if u.message.chat_id == int(chat_id)]
    return chat_updates

async def send_message(bot: telegram.Bot, chat_id: str, text: str):
    """Sends a message to a given chat ID."""
    await bot.send_message(chat_id=chat_id, text=text)
