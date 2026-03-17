import os
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .logging_config import setup_logging
from .routes import auth as auth_router
from .routes import logs as logs_router
from .routes import settings as settings_router
from .routes import tools as tools_router
from tools.registry import registry

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT_DIR / ".env", override=True)
setup_logging()

app = FastAPI(title="Alto AI Backend")

raw_origins = os.getenv("CORS_ORIGINS", "")


def _parse_origins(raw_value: str) -> list[str]:
    # Accept comma/semicolon/whitespace separators and normalize trailing slash.
    parts = re.split(r"[,;\s]+", raw_value or "")
    cleaned: list[str] = []
    for origin in parts:
        value = origin.strip().rstrip("/")
        if value:
            cleaned.append(value)
    return cleaned


origins = _parse_origins(raw_origins)

# Always allow common local webapp dev servers. Keep explicit .env origins too.
default_dev_origins = [
    "http://localhost:3000",
    "https://localhost:3000",
    "http://localhost:4173",
    "https://localhost:4173",
    "http://localhost:5173",
    "https://localhost:5173",
    "http://localhost:5500",
    "https://localhost:5500",
    "http://127.0.0.1:3000",
    "https://127.0.0.1:3000",
    "http://127.0.0.1:4173",
    "https://127.0.0.1:4173",
    "http://127.0.0.1:5173",
    "https://127.0.0.1:5173",
    "http://127.0.0.1:5500",
    "https://127.0.0.1:5500",
]

# De-duplicate while preserving input order.
origins = list(dict.fromkeys(origins + default_dev_origins))

allow_all_origins = "*" in origins
origin_regex = os.getenv("CORS_ORIGIN_REGEX", r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else origins,
    allow_origin_regex=None if allow_all_origins else origin_regex,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(settings_router.router)
app.include_router(tools_router.router)
app.include_router(logs_router.router)


@app.on_event("startup")
def startup():
    registry.scan()


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api.app:app", host="0.0.0.0", port=port, log_level="info")
