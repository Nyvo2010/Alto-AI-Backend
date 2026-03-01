import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from api.auth import create_token, verify_password, decode_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

USER_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "user.json"
_bearer = HTTPBearer()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    token: str
    token_type: str = "bearer"


def require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    subject = decode_token(creds.credentials)
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return subject


def _load_user() -> dict | None:
    if not USER_FILE.exists():
        return None
    return json.loads(USER_FILE.read_text(encoding="utf-8"))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = _load_user()
    if not user:
        raise HTTPException(status_code=500, detail="No admin account configured")

    if body.username != user.get("username"):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(subject=body.username)
    logger.info("Login successful for %s", body.username)
    return TokenResponse(token=token)
