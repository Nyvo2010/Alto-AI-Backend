import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .logging_config import setup_logging
from .routes import auth as auth_router
from .routes import logs as logs_router
from .routes import settings as settings_router
from .routes import tools as tools_router
from tools.registry import registry

load_dotenv()
setup_logging()

app = FastAPI(title="Alto AI Backend")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
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
