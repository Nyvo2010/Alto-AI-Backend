import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = _DIR / "settings.json"
_lock = threading.Lock()


def _ensure_file() -> None:
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text("{}", encoding="utf-8")


def load_all() -> dict[str, Any]:
    _ensure_file()
    with _lock:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))


def save_all(data: dict[str, Any]) -> None:
    _ensure_file()
    with _lock:
        SETTINGS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def get(key: str, default: Any = None) -> Any:
    return load_all().get(key, default)


def put(updates: dict[str, Any]) -> list[str]:
    _ensure_file()
    with _lock:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        data.update(updates)
        SETTINGS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    logger.info("Settings updated: %s", list(updates.keys()))
    return list(updates.keys())


def delete(key: str) -> bool:
    _ensure_file()
    with _lock:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if key not in data:
            return False
        del data[key]
        SETTINGS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    logger.info("Setting deleted: %s", key)
    return True
