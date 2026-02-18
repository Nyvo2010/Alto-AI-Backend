#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# ── 1. Check dependencies ────────────────────────────────────────────────────
echo "Checking dependencies..."

if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Install Python 3.11+ and try again."
  exit 1
fi

PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PY_MINOR" -lt 11 ]; then
  echo "ERROR: Python 3.11+ required."
  exit 1
fi

if ! command -v git &>/dev/null; then
  echo "ERROR: git not found."
  exit 1
fi

# ── 2. Virtual environment ───────────────────────────────────────────────────
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# ── 3. Install dependencies ──────────────────────────────────────────────────
echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# ── 4. Check .env ────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "────────────────────────────────────────────────────────────"
  echo "  .env created from .env.example."
  echo "  Fill in all required values, then run start.sh again."
  echo "────────────────────────────────────────────────────────────"
  exit 0
fi

# Source .env so we can check values
set -o allexport
source .env
set +o allexport

# Required key checks
missing=0
for key in JWT_SECRET MISTRAL_API_KEY GROQ_API_KEY; do
  val=$(eval echo "\$$key")
  if [ -z "$val" ]; then
    echo "ERROR: $key is not set in .env"
    missing=1
  fi
done
[ $missing -eq 1 ] && exit 1

# ── 5. Ensure log directory exists ──────────────────────────────────────────
mkdir -p logs

# ── 6. Create admin user if needed ──────────────────────────────────────────
if [ ! -f "data/user.json" ]; then
  mkdir -p data
  echo ""
  echo "No admin account found. Let's create one."
  .venv/bin/python -m api.auth setup
fi

# ── 7. Deployment note: external port-forwarding ─────────────────────────────
# We no longer use Cloudflare Tunnel. The server binds to 0.0.0.0 so
# your router / port-forwarding should expose the following ports to the
# internet: API (e.g. 8000) and Agent (e.g. 8001). Keep a PID file for processes.
rm -f alto.pid

# ── 8. Launch servers ────────────────────────────────────────────────────────
echo "Starting Settings API..."
nohup .venv/bin/python -m uvicorn api.app:app \
  --host 0.0.0.0 \
  --port "${API_PORT:-8000}" \
  --no-access-log \
  >> logs/alto.log 2>&1 &
echo $! >> alto.pid

echo "Starting Agent Server..."
nohup .venv/bin/python -m agent.server \
  >> logs/alto.log 2>&1 &
echo $! >> alto.pid

# ── 9. Start watcher ───────────────────────────────────────────────────────
echo "Starting watcher..."
nohup bash watcher.sh >> logs/alto.log 2>&1 &
echo $! >> alto.pid

# ── 10. Done ─────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────────────────"
echo "  ✓ Settings API  →  http://localhost:${API_PORT:-8000}"
echo "  ✓ Agent Server  →  http://localhost:${AGENT_PORT:-8001}"
echo "  ✓ Watcher       →  running (checks every 60s)"
echo "  ✓ Logs          →  logs/alto.log (rotating, max 5 MB × 5)"
echo ""
echo "  Live logs URL:  https://logs.alto-ai.tech"
echo "────────────────────────────────────────────────────────────"
