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
    settings: dict


@router.get("")
def get_settings(_user: str = Depends(require_auth)):
    data = store.load_all()
    safe = {k: v for k, v in data.items() if "__token" not in k and "__secret" not in k}
    return {"settings": safe}


@router.put("")
def put_settings(body: SettingsUpdate, _user: str = Depends(require_auth)):
    for key in body.settings:
        if not _valid_key(key):
            raise HTTPException(status_code=400, detail=f"Invalid key: {key}")

    updated = store.put(body.settings)
    return {"updated": updated}


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
