import logging

logger = logging.getLogger(__name__)


async def execute(arguments: dict) -> dict:
    channel_id = arguments.get("channel_id")
    content = arguments.get("content")

    if not channel_id or not content:
        return {"success": False, "error": "channel_id and content are required"}

    from tools.discord.trigger import get_bot

    bot = get_bot()
    if bot is None or not bot.is_ready():
        return {"success": False, "error": "Discord bot is not connected"}

    try:
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            channel = await bot.fetch_channel(int(channel_id))
        await channel.send(content)
        logger.info("Sent message to channel %s", channel_id)
        return {"success": True, "channel_id": channel_id}
    except Exception as e:
        logger.exception("Failed to send Discord message")
        return {"success": False, "error": str(e)}
