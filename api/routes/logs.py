import asyncio
import logging
import os
from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import StreamingResponse

router = APIRouter()
logger = logging.getLogger(__name__)

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'alto.log')


def _validate_token(token: str | None, header_token: str | None) -> bool:
        """
        Validate access to the log stream.

        Behavior:
        - If `LOG_STREAM_TOKEN` is set in the environment, only that value is accepted
            (via either the `?token=` query param or the `X-Log-Token` header).
        - If `LOG_STREAM_TOKEN` is NOT set, fall back to the previous behaviour
            where any non-empty token (query or header) is accepted. This allows
            testing without changing environment variables but is NOT recommended
            for production.
        """
        secret = os.getenv('LOG_STREAM_TOKEN')
        if secret:
                return (token == secret) or (header_token == secret)
        # fallback: accept any non-empty token/header (previous behaviour)
        return bool(token) or bool(header_token)


async def _tail_log(token: str | None, header_token: str | None):
    """
    Async generator that yields SSE-formatted lines from the log file.
    Starts from the last 50 lines so the viewer has context on connect,
    then streams new lines as they are written.
    """
    if not _validate_token(token, header_token):
        yield "data: {\"error\": \"Unauthorized\"}\n\n"
        return

    # Send last 50 lines on connect for immediate context
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-50:]:
                line = line.strip()
                if line:
                    yield f"data: {line}\n\n"
    except FileNotFoundError:
        pass  # Log file doesn't exist yet — that's fine

    # Stream new lines as they arrive
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            f.seek(0, 2)  # Seek to end of file
            while True:
                line = f.readline()
                if line:
                    line = line.strip()
                    if line:
                        yield f"data: {line}\n\n"
                else:
                    # No new line — send a keepalive comment every 15s
                    await asyncio.sleep(1)
                    yield ": keepalive\n\n"
    except asyncio.CancelledError:
        logger.info("Log stream client disconnected")


@router.get('/logs/stream')
async def stream_logs(request: Request, token: str = Query(None, description="Access token")):
    """
    Server-Sent Events endpoint. Streams alto.log in real time.
    Uses ?token= instead of Authorization header because browsers
    cannot send custom headers with EventSource.
    """
    # Accept token either as query param `?token=` or `X-Log-Token` header.
    header_token = request.headers.get('x-log-token')
    return StreamingResponse(
        _tail_log(token, header_token),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',        # Disables Nginx/Caddy buffering
            'Connection': 'keep-alive',
        },
    )
