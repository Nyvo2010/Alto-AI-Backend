#!/usr/bin/env python3
import json
import secrets
import sys
from pathlib import Path
from getpass import getpass

# Add project root to path so we can import api modules if needed
sys.path.append(str(Path(__file__).resolve().parents[1]))

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
ENV_FILE = ROOT_DIR / ".env"
USER_FILE = DATA_DIR / "user.json"

def get_hash(password: str) -> str:
    return pwd_context.hash(password)

def setup_env():
    secret = secrets.token_urlsafe(32)
    env_content = ""
    
    if ENV_FILE.exists():
        env_content = ENV_FILE.read_text()
        
    if "JWT_SECRET=" not in env_content:
        with open(ENV_FILE, "a") as f:
            f.write(f"\nJWT_SECRET={secret}\n")
        print(f"Added JWT_SECRET to {ENV_FILE}")
    else:
        print(f"JWT_SECRET already set in {ENV_FILE}")

def setup_user():
    username = input("Enter username for API access: ")
    password = getpass("Enter password: ")
    confirm = getpass("Confirm password: ")
    
    if password != confirm:
        print("Passwords do not match!")
        return
        
    hashed = get_hash(password)
    
    user_data = {
        "username": username,
        "password_hash": hashed
    }
    
    DATA_DIR.mkdir(exist_ok=True)
    USER_FILE.write_text(json.dumps(user_data, indent=2))
    print(f"User created in {USER_FILE}")

if __name__ == "__main__":
    setup_env()
    setup_user()
