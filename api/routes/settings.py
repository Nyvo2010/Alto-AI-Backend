import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.routes.auth import require_auth
from config import store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(__[a-z0-9_]+)*$")


class SettingsUpdate(BaseModel):
    settings: dict = {}


@router.get("")
def get_settings(_user: str = Depends(require_auth)):
    data = store.load_all()
    # Filter and convert keys
    safe = {}
    for k, v in data.items():
        if "__token" in k or "__secret" in k:
            continue
        # Convert __ to . for frontend
        frontend_key = k.replace("__", ".")
        safe[frontend_key] = v
    return {"settings": safe}


@router.put("")
def put_settings(body: dict, _user: str = Depends(require_auth)):
    # Flatten if wrapped in "settings" key, though check if it is direct.
    # The requirement says body is the settings object.
    # Use body directly.
    settings_to_update = body
    
    # Check if 'settings' key wraps the actual settings (common pattern compatibility)
    if "settings" in body and isinstance(body["settings"], dict) and len(body) == 1:
        settings_to_update = body["settings"]

    # Convert dot notation to double underscore for backend storage
    mapped_settings = {}
    for key, value in settings_to_update.items():
        backend_key = key.replace(".", "__")
        if not _valid_key(backend_key):
             # Allow loose keys if pattern doesn't match but log/warn?
             # For now, stick to validation.
             if not _KEY_PATTERN.match(backend_key):
                 raise HTTPException(status_code=400, detail=f"Invalid key format: {key}")
        mapped_settings[backend_key] = value

    store.put(mapped_settings)
    return {"success": True, "message": "Settings saved successfully"}


@router.delete("/{key}")
def delete_setting(key: str, _user: str = Depends(require_auth)):
    if not _valid_key(key):
        raise HTTPException(status_code=400, detail=f"Invalid key: {key}")
    removed = store.delete(key)
    if not removed:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"deleted": key}


def _valid_key(key: str) -> bool:
    return bool(_KEY_PATTERN.match(key))
