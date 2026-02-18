#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

info() { echo "[INFO] $*"; }
err() { echo "[ERROR] $*" >&2; }

check_cmd() { command -v "$1" >/dev/null 2>&1; }

info "Starting Alto-AI Backend macOS setup wizard"

# 1) Ensure git present
if ! check_cmd git; then
  err "git is required. Please install Xcode command line tools or git and re-run."
  exit 1
fi

# 2) Homebrew (optional but recommended)
if ! check_cmd brew; then
  echo "Homebrew not found. I can install it (requires user approval). Continue? [y/N]"
  read -r REPLY
  if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
  else
    echo "Please install Homebrew and re-run this script." && exit 1
  fi
fi

# 3) Ensure Python 3.11+ installed
if check_cmd python3; then
  PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)') || PY_MINOR=0
else
  PY_MINOR=0
fi

if [ "$PY_MINOR" -lt 11 ]; then
  info "Installing Python 3.11 via Homebrew"
  brew install python@3.11
  export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"
fi

# 4) Ensure Caddy
if ! check_cmd caddy; then
  info "Installing Caddy via Homebrew"
  brew install caddy
fi

# 5) Create venv and install requirements
if [ ! -d ".venv" ]; then
  info "Creating virtual environment (.venv)"
  python3 -m venv .venv
fi

source .venv/bin/activate
info "Upgrading pip and installing Python dependencies"
pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null

# 6) Prepare .env
if [ ! -f ".env" ]; then
  cp .env.example .env
  info ".env created from .env.example"
fi

# Helper to set or generate variable
set_or_gen() {
  key="$1"; prompt="$2"; gen_cmd="$3"
  current=$(grep -E "^${key}=" .env || true)
  val=${current#*=}
  if [ -z "$val" ]; then
    if [ -n "$gen_cmd" ]; then
      val=$(eval "$gen_cmd")
      echo "${key}=${val}" >> .env
      info "Generated ${key} and added to .env"
    else
      echo -n "${prompt}: "
      read -r userval
      echo "${key}=${userval}" >> .env
    fi
  else
    info "${key} already set in .env"
  fi
}

# Generate strong secrets if missing
set_or_gen JWT_SECRET "JWT secret (press enter to auto-generate)" "openssl rand -hex 32"
set_or_gen LOG_STREAM_TOKEN "Log stream token (press enter to auto-generate)" "openssl rand -hex 24"

info "Ensure you have set any provider keys (MISTRAL_API_KEY, GROQ_API_KEY) in .env if needed"

# 7) Write Caddyfile using header injection (recommended)
LOG_TOKEN=$(grep -E '^LOG_STREAM_TOKEN=' .env | sed 's/^LOG_STREAM_TOKEN=//')
if [ -z "$LOG_TOKEN" ]; then
  err "LOG_STREAM_TOKEN not set — aborting Caddy setup"
else
  CADDY_PATHS=("/opt/homebrew/etc/caddy/Caddyfile" "/usr/local/etc/caddy/Caddyfile" "/etc/caddy/Caddyfile")
  selected_path=""
  for p in "${CADDY_PATHS[@]}"; do
    dir=$(dirname "$p")
    if [ -d "$dir" ] || sudo mkdir -p "$dir" 2>/dev/null; then
      selected_path="$p"
      break
    fi
  done

  if [ -z "$selected_path" ]; then
    err "Couldn't determine Caddyfile path. Please place a Caddyfile manually."
  else
    info "Writing Caddyfile to $selected_path (sudo may be required)"
    cat > /tmp/Caddyfile.$$ <<EOF
api.alto-ai.tech {
    reverse_proxy localhost:8000
}

logs.alto-ai.tech {
    reverse_proxy localhost:8000 {
        header_up X-Log-Token "$LOG_TOKEN"
    }
}
EOF
    sudo mv /tmp/Caddyfile.$$ "$selected_path"
    sudo chown root:wheel "$selected_path" || true
    info "Caddyfile written. Starting/restarting Caddy service."
    # Try to use brew services; fall back to running caddy in foreground (not ideal)
    if check_cmd brew; then
      brew services restart caddy || sudo brew services restart caddy || true
    else
      sudo pkill caddy || true
      sudo caddy run --config "$selected_path" &
    fi
  fi
fi

# 8) Start the application using existing start script
info "Launching application (this will create venv and admin user if needed)."
chmod +x start.sh watcher.sh stop.sh
./start.sh

# 9) Show public IP and ask to notify repo owner for DNS
info "Fetching public IP — send this to the domain owner so they can add A records"
PUB_IP=$(curl -fsS https://ifconfig.co || curl -fsS https://ipinfo.io/ip || true)
echo "Public IP: ${PUB_IP}"
echo "Please send this IP to the domain owner (or wait while you and the owner coordinate)."
echo -n "Press Enter after DNS (api.alto-ai.tech & logs.alto-ai.tech) point to this machine (or type skip to continue): "
read -r CONFIRM

if [ "$CONFIRM" != "skip" ]; then
  info "Waiting for DNS to resolve and Caddy to obtain certificates (may take a minute)"
  for i in {1..30}; do
    if curl -fsS -I https://api.alto-ai.tech >/dev/null 2>&1; then
      info "api.alto-ai.tech reachable over HTTPS"
      break
    fi
    sleep 2
  done
fi

info "Setup complete. Quick tests:"
echo "  - API health: https://api.alto-ai.tech/health (or http://localhost:8000/health)"
echo "  - Logs stream: https://logs.alto-ai.tech/logs/stream?token="$(grep -E '^LOG_STREAM_TOKEN=' .env | sed 's/^LOG_STREAM_TOKEN=//')

info "If DNS hasn't been configured yet, stop here, configure DNS, then re-run './setup_mac.sh' or restart Caddy."
