import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
ROUTES_FILE = MEMORY_DIR / "routes.jsonl"


def _ensure_dir() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _append_jsonl(file: Path, entry: dict) -> None:
    with open(file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _read_jsonl(file: Path) -> list[dict]:
    if not file.exists():
        return []

    content = file.read_text(encoding="utf-8").strip()
    if not content:
        return []

    entries = []
    for line in content.splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def save(user_id: str, app: str, summary: str) -> None:
    _ensure_dir()
    entry = {
        "user_id": user_id,
        "app": app,
        "summary": summary,
        "timestamp": time.time(),
    }
    app_file = MEMORY_DIR / f"{app}_{user_id}.jsonl"
    user_file = MEMORY_DIR / f"user_{user_id}.jsonl"
    _append_jsonl(app_file, entry)
    _append_jsonl(user_file, entry)
    logger.info("Memory saved for %s:%s", app, user_id)


def load(user_id: str, app: str, limit: int = 5) -> list[str]:
    _ensure_dir()
    app_file = MEMORY_DIR / f"{app}_{user_id}.jsonl"
    user_file = MEMORY_DIR / f"user_{user_id}.jsonl"

    entries = _read_jsonl(app_file) + _read_jsonl(user_file)
    if not entries:
        return []

    # Deduplicate entries that can be present in both app and user files.
    deduped = {}
    for e in entries:
        key = (
            str(e.get("timestamp", "")),
            str(e.get("app", "")),
            str(e.get("summary", "")),
        )
        deduped[key] = e

    ordered = sorted(
        deduped.values(),
        key=lambda e: e.get("timestamp", 0),
        reverse=True,
    )

    formatted: list[str] = []
    for e in ordered:
        summary = str(e.get("summary", "")).strip()
        if not summary:
            continue
        entry_app = str(e.get("app", "")).strip()
        if entry_app and entry_app != app:
            formatted.append(f"[from {entry_app}] {summary}")
        else:
            formatted.append(summary)
        if len(formatted) >= limit:
            break

    return formatted


def load_all_for_user(user_id: str, limit: int = 10) -> list[str]:
    _ensure_dir()
    all_entries = []
    user_file = MEMORY_DIR / f"user_{user_id}.jsonl"

    all_entries.extend(_read_jsonl(user_file))
    for file in MEMORY_DIR.glob(f"*_{user_id}.jsonl"):
        all_entries.extend(_read_jsonl(file))

    deduped = {}
    for e in all_entries:
        key = (
            str(e.get("timestamp", "")),
            str(e.get("app", "")),
            str(e.get("summary", "")),
        )
        deduped[key] = e

    ordered = sorted(
        deduped.values(),
        key=lambda e: e.get("timestamp", 0),
        reverse=True,
    )

    summaries = []
    for e in ordered:
        summary = str(e.get("summary", "")).strip()
        if summary:
            summaries.append(summary)
        if len(summaries) >= limit:
            break
    return summaries


def log_route_event(
    *,
    event_type: str,
    source_app: str | None,
    source_user_id: str | None,
    source_channel_id: str | None,
    target_app: str | None = None,
    target_channel_id: str | None = None,
    function_name: str | None = None,
) -> None:
    _ensure_dir()
    entry = {
        "event_type": event_type,
        "source_app": source_app,
        "source_user_id": source_user_id,
        "source_channel_id": source_channel_id,
        "target_app": target_app,
        "target_channel_id": target_channel_id,
        "function_name": function_name,
        "timestamp": time.time(),
    }
    _append_jsonl(ROUTES_FILE, entry)
    logger.info(
        "Route event logged: %s %s:%s -> %s:%s",
        event_type,
        source_app or "?",
        source_channel_id or "?",
        target_app or "?",
        target_channel_id or "?",
    )


def load_route_hints(
    *,
    channel_id: str | None,
    user_id: str | None,
    limit: int = 8,
) -> list[str]:
    _ensure_dir()
    entries = _read_jsonl(ROUTES_FILE)
    if not entries:
        return []

    entries.sort(key=lambda e: e.get("timestamp", 0), reverse=True)

    hints: list[str] = []
    seen: set[str] = set()
    for e in entries:
        if e.get("event_type") != "outbound":
            continue

        src_app = _safe_str(e.get("source_app"))
        src_channel = _safe_str(e.get("source_channel_id"))
        src_user = _safe_str(e.get("source_user_id"))
        dst_app = _safe_str(e.get("target_app"))
        dst_channel = _safe_str(e.get("target_channel_id"))
        fn_name = _safe_str(e.get("function_name"))

        if not dst_app or not dst_channel:
            continue

        relevant = False
        if channel_id and (src_channel == channel_id or dst_channel == channel_id):
            relevant = True
        elif user_id and src_user == user_id:
            relevant = True

        if not relevant:
            continue

        route_key = f"{src_app}:{src_channel}->{dst_app}:{dst_channel}:{fn_name}"
        if route_key in seen:
            continue
        seen.add(route_key)

        when = _format_timestamp(e.get("timestamp"))
        hints.append(
            f"{src_app}:{src_channel} -> {dst_app}:{dst_channel} via {fn_name} ({when})"
        )

        if len(hints) >= limit:
            break

    return hints


def _format_timestamp(value) -> str:
    try:
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return "unknown time"


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value)
