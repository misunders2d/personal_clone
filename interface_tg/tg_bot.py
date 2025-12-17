import json
import logging

from telegram import Chat, Message, MessageReactionUpdated, Update, User
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from personal_clone import config
from runner_modules import (
    create_runner,
    format_messaage_content,
    get_or_create_session,
    query_agent,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def extract_user_info(user: User | None) -> str:
    if not user:
        return "None"
    return f"User(id={user.id}, full_name='{user.full_name}', username='@{user.username}', is_bot={user.is_bot})"


def extract_chat_info(chat: Chat | None) -> str:
    if not chat:
        return "None"
    return f"Chat(id={chat.id}, title='{chat.title}', type='{chat.type}', username='@{chat.username}')"


def extract_message_info(message: Message | None, label: str = "Message") -> list[str]:
    if not message:
        return []

    info = [f"--- {label} ---"]
    info.append(f"ID: {message.message_id}")
    info.append(f"Date: {message.date}")
    info.append(f"From: {extract_user_info(message.from_user)}")
    info.append(f"Chat: {extract_chat_info(message.chat)}")

    # Text content
    if message.text:
        info.append(f"Text: {message.text}")
    if message.caption:
        info.append(f"Caption: {message.caption}")

    # Media
    if message.photo:
        largest_photo = message.photo[-1]
        info.append(
            f"Photo: file_id={largest_photo.file_id}, size={largest_photo.width}x{largest_photo.height}"
        )

    if message.document:
        info.append(
            f"Document: name='{message.document.file_name}', mime='{message.document.mime_type}', file_id={message.document.file_id}"
        )

    if message.audio:
        info.append(
            f"Audio: title='{message.audio.title}', performer='{message.audio.performer}', file_id={message.audio.file_id}"
        )

    if message.voice:
        info.append(
            f"Voice: duration={message.voice.duration}s, file_id={message.voice.file_id}"
        )

    if message.video:
        info.append(
            f"Video: name='{message.video.file_name}', duration={message.video.duration}s, file_id={message.video.file_id}"
        )

    if message.video_note:
        info.append(
            f"Video Note: duration={message.video_note.duration}s, file_id={message.video_note.file_id}"
        )

    if message.sticker:
        info.append(
            f"Sticker: emoji='{message.sticker.emoji}', set='{message.sticker.set_name}', file_id={message.sticker.file_id}"
        )

    if message.animation:
        info.append(
            f"Animation: name='{message.animation.file_name}', file_id={message.animation.file_id}"
        )

    if message.poll:
        info.append(
            f"Poll: question='{message.poll.question}', id={message.poll.id}, type={message.poll.type}"
        )

    # Location / Venue
    if message.location:
        info.append(
            f"Location: lat={message.location.latitude}, lon={message.location.longitude}"
        )
    if message.venue:
        info.append(
            f"Venue: title='{message.venue.title}', address='{message.venue.address}'"
        )

    # Entities (Mentions, hashtags, etc.)
    if message.entities:
        entities_str = ", ".join(
            [f"{e.type} (offset={e.offset}, len={e.length})" for e in message.entities]
        )
        info.append(f"Entities: {entities_str}")

    # Forward info
    if message.forward_origin:
        info.append(f"Forward Origin: {message.forward_origin}")
    elif message.date:
        info.append(f"Forwarded: date={message.date}")

    # Reply info
    if message.reply_to_message:
        info.extend(
            extract_message_info(message.reply_to_message, label="Reply To Message")
        )

    # Quote (if replying with quote)
    if message.quote:
        info.append(
            f"Quote: text='{message.quote.text}', position={message.quote.position}"
        )

    return info


def extract_reaction_info(reaction: MessageReactionUpdated) -> list[str]:
    info = ["--- Message Reaction Updated ---"]
    info.append(f"Chat: {extract_chat_info(reaction.chat)}")
    info.append(f"Message ID: {reaction.message_id}")
    if reaction.user:
        info.append(f"User: {extract_user_info(reaction.user)}")
    if reaction.actor_chat:
        info.append(f"Actor Chat: {extract_chat_info(reaction.actor_chat)}")

    info.append(f"Date: {reaction.date}")

    old_reactions = [str(r) for r in reaction.old_reaction]
    new_reactions = [str(r) for r in reaction.new_reaction]

    info.append(f"Old Reactions: {old_reactions}")
    info.append(f"New Reactions: {new_reactions}")
    return info


async def echo_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Explicitly extracts information from the update and echoes it back.
    """
    try:
        lines = [f"Update ID: {update.update_id}"]

        # Check for different update types
        if update.message:
            lines.extend(extract_message_info(update.message, "Message"))

        elif update.edited_message:
            lines.extend(extract_message_info(update.edited_message, "Edited Message"))

        elif update.channel_post:
            lines.extend(extract_message_info(update.channel_post, "Channel Post"))

        elif update.edited_channel_post:
            lines.extend(
                extract_message_info(update.edited_channel_post, "Edited Channel Post")
            )

        elif update.message_reaction:
            lines.extend(extract_reaction_info(update.message_reaction))

        elif update.inline_query:
            lines.append("--- Inline Query ---")
            lines.append(f"From: {extract_user_info(update.inline_query.from_user)}")
            lines.append(f"Query: {update.inline_query.query}")

        elif update.callback_query:
            lines.append("--- Callback Query ---")
            lines.append(f"From: {extract_user_info(update.callback_query.from_user)}")
            lines.append(f"Data: {update.callback_query.data}")
            if update.callback_query.message:
                lines.extend(
                    extract_message_info(
                        update.callback_query.message, "Callback Message"
                    )
                )

        elif update.my_chat_member:
            lines.append("--- My Chat Member Updated ---")
            lines.append(f"Chat: {extract_chat_info(update.my_chat_member.chat)}")
            lines.append(f"From: {extract_user_info(update.my_chat_member.from_user)}")
            lines.append(f"Old Status: {update.my_chat_member.old_chat_member.status}")
            lines.append(f"New Status: {update.my_chat_member.new_chat_member.status}")

        elif update.chat_member:
            lines.append("--- Chat Member Updated ---")
            lines.append(f"Chat: {extract_chat_info(update.chat_member.chat)}")
            lines.append(f"From: {extract_user_info(update.chat_member.from_user)}")
            lines.append(f"Old Status: {update.chat_member.old_chat_member.status}")
            lines.append(f"New Status: {update.chat_member.new_chat_member.status}")

        else:
            lines.append("--- Unknown/Unhandled Update Type ---")
            lines.append(json.dumps(update.to_dict(), indent=2, default=str))

        # Join all lines
        full_text = "\n".join(lines)

        formatted_message = {"text": full_text}
        session_id = await get_or_create_session(
            user_id=str(update.effective_user.id), app_name=config.APP_NAME
        )

        # Send response
        # We use effective_chat if available to send the echo back
        if update.effective_chat:
            async for event in query_agent(
                runner=await create_runner(),
                user_id=str(update.effective_user.id),
                session_id=session_id.id,
                new_message=format_messaage_content(formatted_message),
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            for x in range(0, len(part.text), 4000):
                                await context.bot.send_message(
                                    chat_id=update.effective_chat.id,
                                    text=part.text[x : x + 4000],
                                )
        else:
            logger.info(f"Received update without effective chat: {full_text}")

    except Exception as e:
        logger.error(f"Error in echo_all: {e}", exc_info=True)


def run_bot():
    """
    Runs the Telegram bot.
    """
    if not config.TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set in config.")
        return

    application = ApplicationBuilder().token(config.TELEGRAM_TOKEN).build()

    # Handle ALL updates
    echo_handler = MessageHandler(filters.ALL, echo_all)
    application.add_handler(echo_handler)

    logger.info("Starting Telegram Bot...")
    application.run_polling()


if __name__ == "__main__":
    run_bot()
