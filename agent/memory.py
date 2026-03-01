import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"


def _ensure_dir() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def save(user_id: str, app: str, summary: str) -> None:
    _ensure_dir()
    entry = {
        "user_id": user_id,
        "app": app,
        "summary": summary,
        "timestamp": time.time(),
    }
    file = MEMORY_DIR / f"{app}_{user_id}.jsonl"
    with open(file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.info("Memory saved for %s:%s", app, user_id)


def load(user_id: str, app: str, limit: int = 5) -> list[str]:
    _ensure_dir()
    file = MEMORY_DIR / f"{app}_{user_id}.jsonl"
    if not file.exists():
        return []

    entries = []
    for line in file.read_text(encoding="utf-8").strip().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    entries.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
    return [e["summary"] for e in entries[:limit]]


def load_all_for_user(user_id: str, limit: int = 10) -> list[str]:
    _ensure_dir()
    all_entries = []
    for file in MEMORY_DIR.glob(f"*_{user_id}.jsonl"):
        for line in file.read_text(encoding="utf-8").strip().splitlines():
            try:
                all_entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    all_entries.sort(key=lambda e: e.get("timestamp", 0), reverse=True)
    return [e["summary"] for e in all_entries[:limit]]
