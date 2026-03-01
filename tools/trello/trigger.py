import asyncio
import logging
import os

import httpx

from config.store import get as get_setting

logger = logging.getLogger(__name__)

TRELLO_API_BASE = "https://api.trello.com/1"

_seen_card_ids: set[str] = set()
_pipeline_callback = None


async def start(pipeline_callback) -> None:
    global _pipeline_callback
    _pipeline_callback = pipeline_callback

    api_key = os.getenv("TRELLO_API_KEY", "")
    api_token = os.getenv("TRELLO_API_TOKEN", "")
    if not api_key or not api_token:
        logger.error("Trello API credentials not set, Trello trigger disabled")
        return

    board_id = get_setting("trello__board_id", "")
    if not board_id:
        logger.error("trello__board_id not configured, Trello trigger disabled")
        return

    poll_interval = get_setting("trello__poll_interval", 30)
    logger.info("Trello trigger started (board=%s, interval=%ds)", board_id, poll_interval)

    async with httpx.AsyncClient() as client:
        await _seed_seen(client, api_key, api_token, board_id)

        while True:
            try:
                await _poll(client, api_key, api_token, board_id)
            except Exception:
                logger.exception("Trello poll error")
            await asyncio.sleep(poll_interval)


async def _seed_seen(
    client: httpx.AsyncClient,
    api_key: str,
    api_token: str,
    board_id: str,
) -> None:
    try:
        cards = await _fetch_cards(client, api_key, api_token, board_id)
        for card in cards:
            _seen_card_ids.add(card["id"])
        logger.info("Seeded %d existing Trello cards", len(_seen_card_ids))
    except Exception:
        logger.exception("Failed to seed Trello cards")


async def _poll(
    client: httpx.AsyncClient,
    api_key: str,
    api_token: str,
    board_id: str,
) -> None:
    cards = await _fetch_cards(client, api_key, api_token, board_id)

    for card in cards:
        if card["id"] in _seen_card_ids:
            continue
        _seen_card_ids.add(card["id"])

        name = card.get("name", "")
        if "@alto" not in name.lower():
            continue

        message = name.replace("@alto", "").replace("@Alto", "").strip()
        desc = card.get("desc", "")
        if desc:
            message = f"{message}\n\nCard description: {desc}"

        member_id = card.get("idMembers", ["unknown"])[0] if card.get("idMembers") else "trello_user"

        logger.info("Trello trigger: card=%s user=%s", card["id"], member_id)

        if _pipeline_callback:
            asyncio.create_task(
                _pipeline_callback(
                    user_id=str(member_id),
                    app="trello",
                    message=message,
                    context={
                        "card_id": card["id"],
                        "card_name": name,
                        "board_id": board_id,
                        "card_url": card.get("shortUrl", ""),
                    },
                )
            )


async def _fetch_cards(
    client: httpx.AsyncClient,
    api_key: str,
    api_token: str,
    board_id: str,
) -> list[dict]:
    url = f"{TRELLO_API_BASE}/boards/{board_id}/cards"
    resp = await client.get(
        url,
        params={"key": api_key, "token": api_token, "fields": "id,name,desc,idMembers,shortUrl"},
    )
    resp.raise_for_status()
    return resp.json()
