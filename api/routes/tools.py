import logging
import os

from fastapi import APIRouter, Depends, HTTPException

from api.routes.auth import require_auth
from config import store
from tools.registry import registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
def list_tools(_user: str = Depends(require_auth)):
    tools = []
    for m in registry.get_all():
        tools.append({
            "id": m.id,
            "name": m.name,
            "active": registry.is_active(m.id),
            "has_trigger": m.has_trigger,
            "has_tool": m.has_tool,
            "version": m.version,
        })
    return {"tools": tools}


@router.get("/{tool_id}")
def get_tool(tool_id: str, _user: str = Depends(require_auth)):
    manifest = registry.get(tool_id)
    if not manifest:
        raise HTTPException(status_code=404, detail="Tool not found")

    default_enabled = os.getenv("DEFAULT_TOOL_ENABLED", "true").lower() == "true"
    enabled_value = store.get(f"{tool_id}__enabled", default_enabled)

    settings = [
        {
            "key": f"{tool_id}__enabled",
            "label": "Enabled",
            "type": "boolean",
            "source": "settings",
            "description": "Allow Alto to call this integration.",
            "current_value": enabled_value,
            "required_for_activation": False,
        }
    ]

    for s in manifest.settings_schema:
        entry = {**s}
        if s.get("source") == "settings":
            entry["current_value"] = store.get(s["key"])
        elif s.get("source") == "env":
            env_var = s.get("env_var", "")
            entry["configured"] = bool(os.getenv(env_var))
        settings.append(entry)

    return {
        "id": manifest.id,
        "name": manifest.name,
        "description": manifest.description,
        "version": manifest.version,
        "active": registry.is_active(manifest.id),
        "has_trigger": manifest.has_trigger,
        "has_tool": manifest.has_tool,
        "settings": settings,
    }


@router.post("/reload")
def reload_tools(_user: str = Depends(require_auth)):
    registry.scan()
    return {"status": "reloaded", "tools": len(registry.get_all())}
