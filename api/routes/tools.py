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
        is_active = registry.is_active(m.id)
        tools.append({
            "id": m.id,
            "name": m.name,
            "enabled": is_active,
            "status": "connected" if is_active else "disconnected",
            "active": is_active,  # Include for backward compatibility
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

    settings_values = {}
    
    # Process each setting defined in schema
    # Also include the "enabled" setting which is implicit
    default_enabled = os.getenv("DEFAULT_TOOL_ENABLED", "true").lower() == "true"
    enabled_value = store.get(f"{tool_id}__enabled", default_enabled)
    settings_values[f"{tool_id}.enabled"] = enabled_value

    for s in manifest.settings_schema:
        if s.get("source") != "settings":
            continue
            
        key = s["key"]
        val = store.get(key, s.get("default"))

        # Convert key __ to .
        frontend_key = key.replace("__", ".")
        settings_values[frontend_key] = val

    return {
        "id": manifest.id,
        "name": manifest.name,
        "description": manifest.description,
        "version": manifest.version,
        "active": registry.is_active(manifest.id),
        "settings": settings_values,  # Simplified key-value map
    }


@router.post("/reload")
def reload_tools(_user: str = Depends(require_auth)):
    registry.scan()
    return {"status": "reloaded", "tools": len(registry.get_all())}
