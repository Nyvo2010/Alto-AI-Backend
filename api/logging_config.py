import logging
import logging.handlers
import json
import os
from datetime import datetime, timezone

LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'logs', 'alto.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()


class JSONFormatter(logging.Formatter):
    """Formats every log record as a single-line JSON object.

    This is intended for log files and other machine‑consumable outputs.
    We include additional record metadata so that the entry can be filtered or
    analysed later (module, filename, line number, etc.).
    """

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, object] = {
            'ts': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'filename': record.filename,
            'lineno': record.lineno,
            'msg': record.getMessage(),
        }
        if record.exc_info:
            data['exc'] = self.formatException(record.exc_info)
        return json.dumps(data)


def setup_logging() -> None:
    """
    Call once at application startup (in start.sh entry points).
    Sets up:
      - Rotating file handler → logs/alto.log  (JSON)
      - Stream handler → stdout                 (JSON)
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    # JSON formatter for persistent logs (file, external collectors)
    json_formatter = JSONFormatter()

    # human-friendly formatter for console output
    human_fmt = (
        "%(asctime)s %(levelname)-8s [%(name)s] %(message)s "
        "(%(filename)s:%(lineno)d)"
    )
    human_formatter = logging.Formatter(human_fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # Rotating file — 5 MB max, keep 5 backups
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8',
    )
    file_handler.setFormatter(json_formatter)

    # Stdout uses human formatter so it's easy to read in real time
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(human_formatter)

    root = logging.getLogger()
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    # Suppress noisy third-party loggers
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
