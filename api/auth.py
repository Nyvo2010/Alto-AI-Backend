import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24
USER_FILE = Path(__file__).resolve().parent.parent / "data" / "user.json"


def _secret() -> str:
    secret = os.getenv("JWT_SECRET", "")
    if not secret:
        raise RuntimeError("JWT_SECRET is not set")
    return secret


def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": subject, "exp": expire},
        _secret(),
        algorithm=ALGORITHM,
    )


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def _setup_admin() -> None:
    USER_FILE.parent.mkdir(parents=True, exist_ok=True)
    username = input("Username: ").strip()
    password = input("Password: ").strip()
    if not username or not password:
        print("Username and password are required.")
        sys.exit(1)
    data = {"username": username, "password_hash": hash_password(password)}
    USER_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Admin user '{username}' created.")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        _setup_admin()
    else:
        print("Usage: python -m api.auth setup")
