import json
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


def select_tools(
    user_message: str,
    tool_descriptions: list[dict],
    tool_ids: list[str],
) -> list[str]:
    prompt = (
        "You are a tool selector. Given a user message and available tools, "
        "return ONLY a JSON array of tool IDs that are needed to handle this message.\n\n"
        f"Available tools:\n{json.dumps(tool_descriptions, indent=2)}\n\n"
        f"Tool IDs: {json.dumps(tool_ids)}\n\n"
        f"User message: {user_message}\n\n"
        "Respond with a JSON array of tool IDs only, no explanation. "
        "If no tools are needed, respond with []."
    )

    response = _get_client().chat.completions.create(
        model=_model(),
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=256,
    )

    raw = response.choices[0].message.content.strip()
    try:
        selected = json.loads(raw)
        if isinstance(selected, list):
            valid = [tid for tid in selected if tid in tool_ids]
            logger.info("Tool preselect: %s → %s", user_message[:80], valid)
            return valid
    except json.JSONDecodeError:
        logger.warning("Groq returned invalid JSON for tool selection: %s", raw)

    return tool_ids
