import asyncio
import logging
import os
from threading import Thread

from slack_bolt import App
from slack_bolt.request import BoltRequest
from config.store import get as get_setting

logger = logging.getLogger(__name__)

_client = None
_app = None
_pipeline_callback = None
_server_thread = None


def set_pipeline_callback(callback) -> None:
    global _pipeline_callback
    _pipeline_callback = callback


def get_client():
    return _client


async def start(pipeline_callback) -> None:
    global _client, _app, _pipeline_callback, _server_thread
    _pipeline_callback = pipeline_callback

    bot_token = os.getenv("SLACK_BOT_TOKEN", "")
    signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")

    if not bot_token:
        logger.error("SLACK_BOT_TOKEN not set, Slack trigger disabled")
        return

    if not signing_secret:
        logger.error("SLACK_SIGNING_SECRET not set, Slack trigger disabled")
        return

    try:
        _app = App(token=bot_token, signing_secret=signing_secret)
        _client = _app.client

        @_app.event("message")
        def handle_message(ack, body, logger):
            ack()
            message = body.get("event", {})
            asyncio.create_task(_handle_message_async(message))

        @_app.event("app_mention")
        def handle_mention(ack, body, logger):
            ack()
            message = body.get("event", {})
            asyncio.create_task(_handle_message_async(message))

        logger.info("Slack app initialized with webhooks")

        # Start Flask/Bolt server in a thread
        def run_slack_server():
            try:
                # Default port 3000 for Slack webhook
                port = os.getenv("SLACK_WEBHOOK_PORT", "3000")
                logger.info("Starting Slack webhook server on port %s", port)
                _app.start(port=int(port))
            except Exception:
                logger.exception("Slack webhook server failed")

        _server_thread = Thread(target=run_slack_server, daemon=True)
        _server_thread.start()
        logger.info("Slack webhook server started in background thread")

    except Exception:
        logger.exception("Failed to initialize Slack trigger")


async def _handle_message_async(message: dict) -> None:
    try:
        user_id = message.get("user")
        channel_id = message.get("channel")
        content = message.get("text", "")

        if not user_id or not content:
            return

        # Check allowed users
        allowed_users = get_setting("slack__allowed_users", [])
        if allowed_users and user_id not in allowed_users:
            logger.info("Ignored message from non-allowed user %s", user_id)
            return

        # Check allowed channels
        allowed_channels = get_setting("slack__allowed_channels", [])
        if allowed_channels and channel_id not in allowed_channels:
            logger.info("Ignored message from non-allowed channel %s", channel_id)
            return

        logger.info(
            "Slack trigger: user=%s channel=%s",
            user_id,
            channel_id,
        )

        if _pipeline_callback:
            response = await _pipeline_callback(
                user_id=user_id,
                app="slack",
                message=content,
                context={
                    "channel_id": channel_id,
                    "thread_ts": message.get("thread_ts"),
                    "user_name": message.get("username"),
                },
            )
            if response:
                _client.chat_postMessage(
                    channel=channel_id,
                    text=response,
                    thread_ts=message.get("thread_ts"),
                )
    except Exception:
        logger.exception("Error handling Slack message")
