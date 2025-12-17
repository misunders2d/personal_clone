import logging
import json
import asyncio
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from personal_clone import config

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize AsyncApp
app = AsyncApp(token=config.SLACK_BOT_TOKEN)


def extract_event_info(event: dict) -> list[str]:
    """
    Extracts detailed information from a Slack event.
    """
    info = [f"--- Event Type: {event.get('type', 'unknown')} ---"]

    # Common fields
    if "user" in event:
        info.append(f"User: {event['user']}")
    if "channel" in event:
        info.append(f"Channel: {event['channel']}")
    if "ts" in event:
        info.append(f"Timestamp: {event['ts']}")
    if "event_ts" in event:
        info.append(f"Event Timestamp: {event['event_ts']}")

    # Message specific
    if event.get("type") == "message":
        subtype = event.get("subtype")
        if subtype:
            info.append(f"Subtype: {subtype}")

        if "text" in event:
            info.append(f"Text: {event['text']}")

        if "files" in event:
            for i, file in enumerate(event["files"]):
                info.append(
                    f"File {i+1}: name='{file.get('name')}', type='{file.get('mimetype')}', url='{file.get('url_private')}'"
                )

        if "blocks" in event:
            info.append(f"Blocks: {len(event['blocks'])} blocks")

        if "thread_ts" in event:
            info.append(f"Thread TS: {event['thread_ts']} (Reply)")

        if "edited" in event:
            info.append(
                f"Edited: user={event['edited'].get('user')}, ts={event['edited'].get('ts')}"
            )

    # Reaction specific
    elif (
        event.get("type") == "reaction_added" or event.get("type") == "reaction_removed"
    ):
        info.append(f"Reaction: {event.get('reaction')}")
        info.append(f"Item User: {event.get('item_user')}")
        item = event.get("item", {})
        info.append(
            f"Item: type={item.get('type')}, channel={item.get('channel')}, ts={item.get('ts')}"
        )

    # App mention
    elif event.get("type") == "app_mention":
        info.append(f"Text: {event.get('text')}")

    # Fallback for other fields of interest
    # We can add more specific extractions here as needed

    # Dump the rest of the keys for completeness check
    # info.append(f"Raw Keys: {list(event.keys())}")

    return info


@app.event({"type": "message"})
async def handle_message_events(event, say, logger):
    """
    Handles all message events.
    """
    try:
        # Ignore bot messages to prevent loops
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return

        info = extract_event_info(event)

        # Add raw JSON for full detail if needed, but formatted
        # info.append("--- Raw JSON ---")
        # info.append(json.dumps(event, indent=2))

        message_text = "\n".join(info)

        await say(f"```\n{message_text}\n```")

    except Exception as e:
        logger.error(f"Error handling message: {e}")


@app.event("reaction_added")
async def handle_reaction_added(event, say, logger):
    try:
        info = extract_event_info(event)
        # Reactions happen on items, so 'say' might post to the channel of the item
        channel_id = event.get("item", {}).get("channel")
        if channel_id:
            await app.client.chat_postMessage(
                channel=channel_id, text=f"```\n{'\n'.join(info)}\n```"
            )
    except Exception as e:
        logger.error(f"Error handling reaction_added: {e}")


@app.event("reaction_removed")
async def handle_reaction_removed(event, say, logger):
    try:
        info = extract_event_info(event)
        channel_id = event.get("item", {}).get("channel")
        if channel_id:
            await app.client.chat_postMessage(
                channel=channel_id, text=f"```\n{'\n'.join(info)}\n```"
            )
    except Exception as e:
        logger.error(f"Error handling reaction_removed: {e}")


# Catch-all for other events we might want to see
@app.event(
    dict(type=lambda t: t not in ["message", "reaction_added", "reaction_removed"])
)
async def handle_any_event(event, say, logger):
    # This might be noisy, so we log it or try to echo if it has a channel
    try:
        logger.info(f"Unhandled event type: {event.get('type')}")
        # If it has a channel, we can try to echo
        if "channel" in event:
            info = extract_event_info(event)
            # info.append(json.dumps(event, indent=2))
            await say(f"```\n{'\n'.join(info)}\n```")
    except Exception as e:
        logger.error(f"Error handling generic event: {e}")


async def run_bot():
    if not config.SLACK_APP_TOKEN:
        logger.error("SLACK_APP_TOKEN is not set in config.")
        return

    handler = AsyncSocketModeHandler(app, config.SLACK_APP_TOKEN)
    logger.info("Starting Slack Bot...")
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(run_bot())
