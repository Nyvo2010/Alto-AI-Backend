import asyncio
import json
import logging
from pathlib import Path

from agent import llm, preselect, summarise, memory
from sessions.manager import sessions, Session
from tools.registry import registry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_FILE = Path(__file__).resolve().parent.parent / "system_prompt.txt"


def _load_system_prompt() -> str:
    if SYSTEM_PROMPT_FILE.exists():
        return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
    return "You are Alto, an AI team member."


async def handle_message(
    user_id: str,
    app: str,
    message: str,
    context: dict | None = None,
) -> str:
    session = sessions.get_or_create(user_id, app)

    runtime_context = dict(context or {})
    runtime_context.setdefault("source_app", app)
    runtime_context.setdefault("source_user_id", user_id)
    if "source_channel_id" not in runtime_context and runtime_context.get("channel_id"):
        runtime_context["source_channel_id"] = runtime_context.get("channel_id")

    try:
        memory.log_route_event(
            event_type="inbound",
            source_app=runtime_context.get("source_app"),
            source_user_id=runtime_context.get("source_user_id"),
            source_channel_id=runtime_context.get("source_channel_id"),
        )
    except Exception:
        logger.exception("Failed to log inbound route event")

    if session.needs_mid_summary():
        await _mid_session_summarise(session)

    session.add_message("user", message)

    memories = memory.load(user_id, app, limit=5)
    route_hints = memory.load_route_hints(
        channel_id=runtime_context.get("source_channel_id"),
        user_id=user_id,
        limit=6,
    )

    tool_descs = registry.get_tool_descriptions()
    tool_ids = [d["id"] for d in tool_descs]

    selected_ids = tool_ids
    if tool_ids:
        try:
            selected_ids = await asyncio.to_thread(
                preselect.select_tools, message, tool_descs, tool_ids
            )
        except Exception:
            logger.exception("Tool preselection failed, using all tools")
            selected_ids = tool_ids

    mistral_tools = registry.get_mistral_tools(selected_ids)

    system_prompt = _load_system_prompt()
    if memories:
        memory_text = "\n".join(f"- {m}" for m in memories)
        system_prompt += f"\n\nPrevious context:\n{memory_text}"
    if runtime_context:
        system_prompt += f"\n\nCurrent context: {json.dumps(runtime_context)}"
    if route_hints:
        routes_text = "\n".join(f"- {r}" for r in route_hints)
        system_prompt += (
            "\n\nRecent cross-platform routing history "
            "(use these channel IDs when continuing conversations across platforms):\n"
            f"{routes_text}"
        )

    response = await _run_reasoning_loop(
        session,
        mistral_tools,
        system_prompt,
        runtime_context,
    )

    session.add_message("assistant", response)
    return response


async def _run_reasoning_loop(
    session: Session,
    tools: list[dict],
    system_prompt: str,
    context: dict | None,
    max_iterations: int = 5,
) -> str:
    for _ in range(max_iterations):
        result = await asyncio.to_thread(
            llm.chat,
            messages=session.messages,
            tools=tools if tools else None,
            system_prompt=system_prompt,
        )

        if not result.get("tool_calls"):
            return result.get("content", "")

        session.messages.append(result)

        for tc in result["tool_calls"]:
            func_name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"])
            except (json.JSONDecodeError, TypeError):
                args = {}

            tool_result = await _execute_tool(func_name, args, context)

            session.messages.append({
                "role": "tool",
                "name": func_name,
                "tool_call_id": tc["id"],
                "content": json.dumps(tool_result, ensure_ascii=False),
            })

    return "I've completed the requested actions."


async def _execute_tool(
    function_name: str,
    arguments: dict,
    context: dict | None,
) -> dict:
    tool_id = registry.find_tool_by_function(function_name)
    if not tool_id:
        return {"error": f"Unknown function: {function_name}"}

    executor = registry.get_executor(tool_id)
    if not executor:
        return {"error": f"No executor for tool: {tool_id}"}

    call_arguments = dict(arguments)
    call_arguments["function_name"] = function_name

    if context:
        call_arguments["_context"] = context

    try:
        if asyncio.iscoroutinefunction(executor):
            tool_result = await executor(call_arguments)
        else:
            tool_result = await asyncio.to_thread(executor, call_arguments)

        _log_outbound_route(function_name, tool_result, context)
        return tool_result
    except Exception as e:
        logger.exception("Tool execution failed: %s", function_name)
        return {"error": str(e)}


def _log_outbound_route(
    function_name: str,
    tool_result: dict,
    context: dict | None,
) -> None:
    if not isinstance(tool_result, dict):
        return
    if not tool_result.get("success"):
        return

    target_app = _target_app_from_function(function_name)
    target_channel_id = tool_result.get("channel_id")
    if not target_app or not target_channel_id:
        return

    src = context or {}
    source_app = src.get("source_app")
    source_user_id = src.get("source_user_id")
    source_channel_id = src.get("source_channel_id") or src.get("channel_id")

    try:
        memory.log_route_event(
            event_type="outbound",
            source_app=str(source_app) if source_app is not None else None,
            source_user_id=str(source_user_id) if source_user_id is not None else None,
            source_channel_id=str(source_channel_id) if source_channel_id is not None else None,
            target_app=target_app,
            target_channel_id=str(target_channel_id),
            function_name=function_name,
        )
    except Exception:
        logger.exception("Failed to log outbound route event")


def _target_app_from_function(function_name: str) -> str | None:
    if function_name.startswith("slack_"):
        return "slack"
    if function_name.startswith("discord_"):
        return "discord"
    return None


def on_session_expire(session: Session) -> None:
    try:
        summary = summarise.summarise_for_memory(session.messages)
        if summary:
            memory.save(session.user_id, session.app, summary)
            logger.info("Session memory saved for %s:%s", session.app, session.user_id)
    except Exception:
        logger.exception("Failed to save session memory for %s", session.key)


async def _mid_session_summarise(session: Session) -> None:
    try:
        summary = await asyncio.to_thread(
            summarise.summarise_conversation, session.messages
        )
        session.messages = [
            {"role": "system", "content": f"Conversation summary: {summary}"}
        ]
        session.summary = summary
        logger.info("Mid-session summary for %s", session.key)
    except Exception:
        logger.exception("Mid-session summarisation failed")
