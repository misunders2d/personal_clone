# This file will contain the Telegram agent and its tools.

from google.adk.agents import Agent
from ..utils.telegram_utils import get_telegram_client, get_chat_history
import asyncio

async def get_chat_summary(chat_id: str) -> str:
  """Summarizes a Telegram chat."""
  bot = get_telegram_client()
  history = await get_chat_history(bot, chat_id)
  
  # Create a summary using an LLM
  from google.adk.models import Gemini
  llm = Gemini(model="gemini-1.5-flash")
  
  # Prepare the prompt for the LLM
  prompt = "Please summarize the following chat history:\n"
  for update in history:
      if update.message and update.message.text:
          prompt += f"- {update.message.from_user.username}: {update.message.text}\n"

  # Generate the summary
  response = await llm.generate_content_async(contents=[prompt])
  return response.text


async def create_draft_reply(chat_id: str, user_message: str) -> str:
  """Creates a draft reply to a user's message."""
  bot = get_telegram_client()
  history = await get_chat_history(bot, chat_id)
  
  # Create a draft reply using an LLM
  from google.adk.models import Gemini
  llm = Gemini(model="gemini-1.5-flash")
  
  # Prepare the prompt for the LLM
  prompt = "Please create a draft reply to the last message in the following chat history:\n"
  for update in history:
      if update.message and update.message.text:
          prompt += f"- {update.message.from_user.username}: {update.message.text}\n"
  prompt += f"The user's message to reply to is: {user_message}"

  # Generate the draft reply
  response = await llm.generate_content_async(contents=[prompt])
  return response.text


telegram_agent = Agent(
    name="telegram_agent",
    description="An agent that can manage a Telegram account.",
    instruction="You are an agent that can manage a Telegram account. You can summarize chats and create draft answers.",
    tools=[
        get_chat_summary,
        create_draft_reply,
    ],
)
