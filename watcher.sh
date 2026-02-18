#!/usr/bin/env bash

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

log() {
  # Write directly to log file in JSON format (logging system may not be running)
  echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"level\":\"INFO\",\"logger\":\"watcher\",\"msg\":\"$1\"}"
}

log "Watcher started. Polling every 60s."

while true; do
  sleep 60

  git fetch origin main --quiet 2>/dev/null || {
    log "git fetch failed — check network or repo access"
    continue
  }

  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse origin/main)

  if [ "$LOCAL" = "$REMOTE" ]; then
    log "No update (HEAD=${LOCAL:0:7})"
    continue
  fi

  log "New commit detected (${LOCAL:0:7} → ${REMOTE:0:7}). Restarting..."

  # ── Graceful shutdown ──────────────────────────────────────────────────────
  if [ -f "alto.pid" ]; then
    while IFS= read -r pid; do
      kill -0 "$pid" 2>/dev/null && kill -TERM "$pid"
    done < alto.pid

    for i in {1..10}; do
      all_done=true
      while IFS= read -r pid; do
        kill -0 "$pid" 2>/dev/null && all_done=false
      done < alto.pid
      $all_done && break
      sleep 1
    done

    while IFS= read -r pid; do
      kill -9 "$pid" 2>/dev/null
    done < alto.pid

    rm -f alto.pid
  fi

  # ── Pull and update ────────────────────────────────────────────────────────
  git pull origin main
  source .venv/bin/activate
  pip install --quiet -r requirements.txt

  # ── Relaunch ───────────────────────────────────────────────────────────────
  set -o allexport
  source .env
  set +o allexport

  mkdir -p logs

  # No Cloudflare -- external port-forwarding expected. Services bind to 0.0.0.0

  nohup .venv/bin/python -m uvicorn api.app:app \
    --host 0.0.0.0 \
    --port "${API_PORT:-8000}" \
    --no-access-log \
    >> logs/alto.log 2>&1 &
  echo $! >> alto.pid

  nohup .venv/bin/python -m agent.server \
    >> logs/alto.log 2>&1 &
  echo $! >> alto.pid

  log "Restart complete. New HEAD=$(git rev-parse --short HEAD)"
done
