import logging

logger = logging.getLogger(__name__)


async def execute(arguments: dict) -> dict:
    function_name = arguments.get("function_name")
    
    if function_name == "slack_send_message":
        return await slack_send_message(arguments)
    elif function_name == "slack_add_reaction":
        return await slack_add_reaction(arguments)
    else:
        return {"success": False, "error": f"Unknown function: {function_name}"}


async def slack_send_message(arguments: dict) -> dict:
    channel_id = arguments.get("channel_id")
    content = arguments.get("content")
    thread_ts = arguments.get("thread_ts")

    if not channel_id or not content:
        return {"success": False, "error": "channel_id and content are required"}

    from tools.slack.trigger import get_client

    client = get_client()
    if client is None:
        return {"success": False, "error": "Slack client is not initialized"}

    try:
        kwargs = {
            "channel": channel_id,
            "text": content,
        }
        if thread_ts:
            kwargs["thread_ts"] = thread_ts

        response = client.chat_postMessage(**kwargs)
        logger.info("Sent message to channel %s with ts %s", channel_id, response.get("ts"))
        return {
            "success": True,
            "channel_id": channel_id,
            "timestamp": response.get("ts"),
        }
    except Exception as e:
        logger.exception("Failed to send Slack message")
        return {"success": False, "error": str(e)}


async def slack_add_reaction(arguments: dict) -> dict:
    channel_id = arguments.get("channel_id")
    timestamp = arguments.get("timestamp")
    emoji = arguments.get("emoji")

    if not channel_id or not timestamp or not emoji:
        return {"success": False, "error": "channel_id, timestamp, and emoji are required"}

    from tools.slack.trigger import get_client

    client = get_client()
    if client is None:
        return {"success": False, "error": "Slack client is not initialized"}

    try:
        client.reactions_add(
            channel=channel_id,
            timestamp=timestamp,
            name=emoji,
        )
        logger.info("Added reaction %s to message %s in channel %s", emoji, timestamp, channel_id)
        return {
            "success": True,
            "channel_id": channel_id,
            "timestamp": timestamp,
            "emoji": emoji,
        }
    except Exception as e:
        logger.exception("Failed to add reaction to Slack message")
        return {"success": False, "error": str(e)}
