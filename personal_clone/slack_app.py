import asyncio
import logging
import os

from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from .app_utils.agent_runner import get_runner, reload_runner
from .secure_config import capture_key, check_pending
from .telegram_poller import extract_agent_response, _pending_session_reset, _handle_session_reset

logger = logging.getLogger(__name__)

_slack_handler = None


async def start_slack(process_init_fn):
    """Initializes and starts the Slack Socket Mode handler."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    app_token = os.environ.get("SLACK_APP_TOKEN")

    if not (token and app_token) or token == "********" or app_token == "********":
        logger.info("Slack: Missing tokens, poller idle.")
        return

    try:
        app = AsyncApp(token=token)

        @app.event("message")
        async def handle_message_events(body, logger):
            event = body.get("event", {})
            if event.get("subtype") or event.get("bot_id"):
                return

            text = event.get("text")
            channel = event.get("channel")
            user = event.get("user")

            if not text or not channel:
                return

            user_id = f"slack_{user}"
            session_id = f"slack_channel_{channel}"

            # SECURE KEY CAPTURE: intercept before anything reaches the agent
            if check_pending(session_id):
                result = capture_key(session_id, text)
                # Note: Slack doesn't easily let bots delete user messages,
                # but we still prevent the key from reaching the agent.
                await app.client.chat_postMessage(channel=channel, text=result["message"])
                return

            # SESSION RESET: intercept the user's choice
            if session_id in _pending_session_reset:
                runner = get_runner()
                if runner:
                    result = await _handle_session_reset(
                        runner, user_id, session_id, text
                    )
                    await app.client.chat_postMessage(channel=channel, text=result)
                else:
                    _pending_session_reset.pop(session_id, None)
                return

            # Handle /init via message prefix
            if text.strip().startswith("/init"):
                result = process_init_fn(text)
                await app.client.chat_postMessage(channel=channel, text=result)
                return

            runner = get_runner()
            if not runner:
                await app.client.chat_postMessage(channel=channel, text="Bot not ready. Configure at /setup.")
                return

            try:
                response = await extract_agent_response(runner, user_id, session_id, text)
                await app.client.chat_postMessage(channel=channel, text=response)
            except Exception:
                logger.exception("Error processing Slack message")

        handler = AsyncSocketModeHandler(app, app_token)
        logger.info("Slack: Socket Mode active.")
        await handler.start_async()

    except Exception:
        logger.exception("Failed to start Slack handler")


async def run_slack_forever(process_init_fn):
    """Wrapper to keep the slack task alive."""
    while True:
        try:
            await start_slack(process_init_fn)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Slack handler crashed, restarting in 10s...")
            await asyncio.sleep(10)
