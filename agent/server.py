import asyncio
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI

from agent.pipeline import handle_message, on_session_expire
from sessions.manager import sessions
from tools.registry import registry

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(title="Alto AI Agent")


@app.on_event("startup")
async def startup() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Agent server starting")

    registry.scan()
    logger.info("Loaded %d tools", len(registry.get_all()))

    sessions.on_expire(on_session_expire)
    asyncio.create_task(sessions.cleanup_loop())

    await _start_triggers()


async def _start_triggers() -> None:
    starters = registry.get_trigger_starters()
    for tool_id, starter in starters.items():
        logger.info("Starting trigger: %s", tool_id)
        asyncio.create_task(_run_trigger(tool_id, starter))


async def _run_trigger(tool_id: str, starter) -> None:
    retries = 0
    while True:
        try:
            await starter(handle_message)
        except Exception:
            retries += 1
            wait = min(30 * retries, 300)
            logger.exception("Trigger %s crashed (retry #%d in %ds)", tool_id, retries, wait)
            await asyncio.sleep(wait)
        else:
            break


@app.get("/agent/health")
def agent_health():
    active_tools = [t.id for t in registry.get_active_tools()]
    return {
        "status": "ok",
        "active_tools": active_tools,
        "total_tools": len(registry.get_all()),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("AGENT_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
