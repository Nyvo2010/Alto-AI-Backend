import logging
import os

from groq import Groq

logger = logging.getLogger(__name__)

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        _client = Groq(api_key=api_key)
    return _client


def _model() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def summarise_conversation(messages: list[dict]) -> str:
    text = "\n".join(
        f"{m['role']}: {m['content']}" for m in messages if m.get("content")
    )
    prompt = (
        "Summarise the following conversation concisely. "
        "Keep key facts, decisions, and action items. "
        "Write in third person.\n\n"
        f"{text}"
    )

    response = _get_client().chat.completions.create(
        model=_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=512,
    )
    summary = response.choices[0].message.content.strip()
    logger.info("Summarised %d messages → %d chars", len(messages), len(summary))
    return summary


def summarise_for_memory(messages: list[dict]) -> str | None:
    ai_tokens = sum(
        len(m["content"]) // 4
        for m in messages
        if m["role"] == "assistant" and m.get("content")
    )
    if ai_tokens < 100:
        return None

    return summarise_conversation(messages)
