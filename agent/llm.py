import json
import logging
import os

from mistralai import Mistral

logger = logging.getLogger(__name__)

_client: Mistral | None = None


def _get_client() -> Mistral:
    global _client
    if _client is None:
        api_key = os.getenv("MISTRAL_API_KEY", "")
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY is not set")
        _client = Mistral(api_key=api_key)
    return _client


def _model() -> str:
    return os.getenv("MISTRAL_MODEL", "mistral-large-latest")


def chat(
    messages: list[dict],
    tools: list[dict] | None = None,
    system_prompt: str | None = None,
) -> dict:
    full_messages = []
    if system_prompt:
        full_messages.append({"role": "system", "content": system_prompt})
    full_messages.extend(messages)

    kwargs: dict = {
        "model": _model(),
        "messages": full_messages,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    response = _get_client().chat.complete(**kwargs)
    choice = response.choices[0]
    message = choice.message

    if message.tool_calls:
        return {
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ],
        }

    return {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [],
    }
