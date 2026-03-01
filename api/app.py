from fastapi import FastAPI
import os

from .logging_config import setup_logging
from .routes import logs as logs_router


# Initialize logging early so other modules can use the configured logger
setup_logging()

app = FastAPI(title="Alto AI Backend")

# Mount routes implemented in repo (logs streaming is available)
app.include_router(logs_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    # Quick local runner for development
    import uvicorn
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api.app:app", host="0.0.0.0", port=port, log_level="info")
