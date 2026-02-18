"""
Minimal agent server used by `start.sh` and `watcher.sh` when launching the agent.
This provides a small FastAPI app with a health endpoint and runs uvicorn when
executed as a module: `python -m agent.server`.
"""
import os

from fastapi import FastAPI

app = FastAPI(title="Alto AI Agent")


@app.get("/agent/health")
def agent_health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("AGENT_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
