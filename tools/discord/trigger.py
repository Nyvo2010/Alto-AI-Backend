import asyncio
import logging
import os

import discord

from config.store import get as get_setting

logger = logging.getLogger(__name__)

_bot: discord.Client | None = None
_pipeline_callback = None


def set_pipeline_callback(callback) -> None:
    global _pipeline_callback
    _pipeline_callback = callback


def get_bot() -> discord.Client | None:
    return _bot


async def start(pipeline_callback) -> None:
    global _bot, _pipeline_callback
    _pipeline_callback = pipeline_callback

    token = os.getenv("DISCORD_BOT_TOKEN", "")
    if not token:
        logger.error("DISCORD_BOT_TOKEN not set, Discord trigger disabled")
        return

    intents = discord.Intents.default()
    intents.message_content = True
    _bot = discord.Client(intents=intents)

    @_bot.event
    async def on_ready():
        logger.info("Discord bot connected as %s", _bot.user)

    @_bot.event
    async def on_message(message: discord.Message):
        if message.author == _bot.user:
            return
        if not _bot.user:
            return

        is_mention = _bot.user.mentioned_in(message)
        is_reply = (
            message.reference
            and message.reference.resolved
            and isinstance(message.reference.resolved, discord.Message)
            and message.reference.resolved.author == _bot.user
        )

        if not is_mention and not is_reply:
            return

        allowed_ids = get_setting("discord__allowed_user_ids", [])
        if allowed_ids and str(message.author.id) not in allowed_ids:
            logger.info("Ignored message from non-allowed user %s", message.author.id)
            return

        content = message.content
        if _bot.user:
            content = content.replace(f"<@{_bot.user.id}>", "").strip()
            content = content.replace(f"<@!{_bot.user.id}>", "").strip()

        if not content:
            return

        logger.info(
            "Discord trigger: user=%s channel=%s",
            message.author.id,
            message.channel.id,
        )

        if _pipeline_callback:
            asyncio.create_task(
                _handle_and_reply(message, content)
            )

    async def _handle_and_reply(message: discord.Message, content: str):
        try:
            response = await _pipeline_callback(
                user_id=str(message.author.id),
                app="discord",
                message=content,
                context={
                    "channel_id": str(message.channel.id),
                    "guild_id": str(message.guild.id) if message.guild else None,
                    "author_name": str(message.author),
                },
            )
            if response:
                await message.reply(response)
        except Exception:
            logger.exception("Error handling Discord message")

    try:
        await _bot.start(token)
    except Exception:
        logger.exception("Discord bot crashed")
