import asyncio
import logging
import os

import httpx
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# Session lifecycle: pending reset choices keyed by session_id
_pending_session_reset: dict[str, object] = {}  # session_id -> session object

MAX_SESSION_EVENTS = 200

SESSION_LIMIT_PROMPT = (
    "This conversation has grown very long ({event_count} events) and is "
    "slowing down my responses.\n\n"
    "Please choose how to proceed:\n"
    "1. *Fresh start* — wipe the session completely\n"
    "2. *Carry over context* — summarize this session and start a new one "
    "with the summary\n\n"
    "Reply *1* or *2*."
)


async def send_typing(client: httpx.AsyncClient, token: str, chat_id: int):
    """Send 'typing...' indicator to a Telegram chat."""
    url = TELEGRAM_API.format(token=token, method="sendChatAction")
    try:
        await client.post(url, json={"chat_id": chat_id, "action": "typing"})
    except Exception:
        pass


async def send_message(client: httpx.AsyncClient, token: str, chat_id: int, text: str):
    """Send a message to a Telegram chat."""
    url = TELEGRAM_API.format(token=token, method="sendMessage")
    try:
        resp = await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
        if resp.status_code != 200:
            resp = await client.post(url, json={"chat_id": chat_id, "text": text})
            if resp.status_code != 200:
                logger.error("Telegram sendMessage failed: %s", resp.text)
    except Exception:
        logger.exception("Failed to send Telegram message to chat %s", chat_id)


async def _summarize_session(session) -> str:
    """Use Gemini to summarize session events into a compact context string."""
    texts = []
    for event in session.events:
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    role = event.content.role or "unknown"
                    texts.append(f"{role}: {part.text}")
    if not texts:
        return ""
    conversation = "\n".join(texts[-80:])
    client = genai.Client()
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            "Summarize the following conversation into a concise context briefing. "
            "Preserve key facts, decisions, ongoing tasks, and user preferences. "
            "Keep it under 500 words.\n\n" + conversation
        ),
    )
    return response.text or ""


async def _handle_session_reset(runner, user_id, session_id, choice: str) -> str:
    """Process the user's session reset choice. Returns a status message."""
    session = _pending_session_reset.pop(session_id, None)

    if choice.strip() == "2" and session is not None:
        summary = await _summarize_session(session)
        await runner.session_service.delete_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )
        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )
        if summary:
            await extract_agent_response(
                runner, user_id, session_id,
                f"[CONTEXT FROM PREVIOUS SESSION]\n{summary}\n[END CONTEXT]\n\n"
                "Acknowledge that you have received a summary of our previous "
                "conversation. Briefly confirm what you remember."
            )
            return "New session started with context carried over."
        else:
            return "Could not generate a summary. Started a fresh session instead."
    else:
        await runner.session_service.delete_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )
        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )
        return "Fresh session started."


async def extract_agent_response(runner, user_id: str, session_id: str, text: str) -> str:
    """Run the agent and extract the final text response."""
    try:
        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )
        if session is None:
            await runner.session_service.create_session(
                app_name=runner.app_name, user_id=user_id, session_id=session_id
            )
        elif len(session.events) > MAX_SESSION_EVENTS:
            logger.warning(
                "Session %s hit hard limit (%d events), prompting user.",
                session_id, len(session.events),
            )
            _pending_session_reset[session_id] = session
            return SESSION_LIMIT_PROMPT.format(event_count=len(session.events))
    except Exception:
        await runner.session_service.create_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )

    MAX_RETRIES = 2
    parts = []
    message = types.Content(role="user", parts=[types.Part.from_text(text=text)])

    for attempt in range(1 + MAX_RETRIES):
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=message,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            parts.append(part.text)
            break  # success
        except Exception as exc:
            error_msg = str(exc).split("\n")[0] if str(exc) else type(exc).__name__
            logger.warning(
                "Agent error (attempt %d/%d) for user %s: %s",
                attempt + 1, 1 + MAX_RETRIES, user_id, error_msg,
            )
            if attempt < MAX_RETRIES:
                parts.clear()
                message = types.Content(
                    role="user",
                    parts=[types.Part.from_text(
                        text=(
                            f"Your previous action failed with this error: {error_msg}\n"
                            "Analyze what went wrong and retry my original request. "
                            "If a tool caused the error, do NOT use it again."
                        )
                    )],
                )
                continue
            return f"Agent error after {1 + MAX_RETRIES} attempts. Last error: {error_msg}"

    return "\n".join(parts) if parts else "I processed your request but have no response to show."


async def poll_telegram(process_init_fn):
    """Long-poll Telegram's getUpdates API and process messages."""
    from .app_utils.agent_runner import get_runner

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token or token == "********":
        logger.info("Telegram: No valid token, poller idle.")
        return

    logger.info("Telegram: Polling mode active — listening for messages...")
    offset_file = os.path.join(os.path.abspath("./data"), ".tg_poll_offset")
    offset = 0
    try:
        with open(offset_file) as f:
            offset = int(f.read().strip())
            logger.info("Resumed Telegram poll offset: %d", offset)
    except (FileNotFoundError, ValueError):
        pass

    async with httpx.AsyncClient(timeout=60) as client:
        while True:
            try:
                url = TELEGRAM_API.format(token=token, method="getUpdates")
                resp = await client.get(url, params={"offset": offset, "timeout": 30})
                data = resp.json()

                if not data.get("ok"):
                    logger.warning("Telegram getUpdates returned error: %s", data)
                    await asyncio.sleep(5)
                    continue

                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    try:
                        with open(offset_file, "w") as f:
                            f.write(str(offset))
                    except OSError:
                        pass
                    msg = update.get("message")
                    if not msg or not msg.get("text"):
                        continue

                    text = msg["text"]
                    chat_id = msg["chat"]["id"]
                    from_user = msg.get("from", {})
                    user_id = f"tg_{from_user.get('id', 'unknown')}"
                    session_id = f"tg_chat_{chat_id}"

                    # SESSION RESET: intercept the user's choice
                    if session_id in _pending_session_reset:
                        runner = get_runner()
                        if runner:
                            result = await _handle_session_reset(
                                runner, user_id, session_id, text
                            )
                            await send_message(client, token, chat_id, result)
                        else:
                            _pending_session_reset.pop(session_id, None)
                        continue

                    # Handle /init command
                    if text.strip().startswith("/init"):
                        result = process_init_fn(text)
                        await send_message(client, token, chat_id, result)
                        continue

                    # Handle /start command
                    if text.strip() == "/start":
                        await send_message(client, token, chat_id,
                            "Welcome! Send me a message to get started.")
                        continue

                    runner = get_runner()
                    if not runner:
                        await send_message(client, token, chat_id,
                            "Bot not ready. Configure at /setup.")
                        continue

                    # Show typing indicator while the agent processes
                    async def keep_typing():
                        while True:
                            await send_typing(client, token, chat_id)
                            await asyncio.sleep(4)

                    typing_task = asyncio.create_task(keep_typing())
                    try:
                        response = await extract_agent_response(runner, user_id, session_id, text)
                    finally:
                        typing_task.cancel()
                        try:
                            await typing_task
                        except asyncio.CancelledError:
                            pass

                    await send_message(client, token, chat_id, response)

            except httpx.ReadTimeout:
                continue
            except asyncio.CancelledError:
                logger.info("Telegram poller shutting down")
                return
            except Exception:
                logger.exception("Telegram poller error, retrying in 5s")
                await asyncio.sleep(5)
