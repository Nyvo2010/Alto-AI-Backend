import logging
import logging.handlers
import json
import os
from datetime import datetime, timezone

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'logs', 'alto.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()


class JSONFormatter(logging.Formatter):
    """Formats every log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            'ts': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'msg': record.getMessage(),
            **({'exc': self.formatException(record.exc_info)} if record.exc_info else {}),
        })


def setup_logging() -> None:
    """
    Call once at application startup (in start.sh entry points).
    Sets up:
      - Rotating file handler → logs/alto.log  (JSON)
      - Stream handler → stdout                 (JSON)
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    formatter = JSONFormatter()

    # Rotating file — 5 MB max, keep 5 backups
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
    )
    file_handler.setFormatter(formatter)

    # Stdout
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    # Suppress noisy third-party loggers
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
