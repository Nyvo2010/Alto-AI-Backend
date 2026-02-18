#!/usr/bin/env bash

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

if [ ! -f "alto.pid" ]; then
  echo "No alto.pid found — nothing to stop."
  exit 0
fi

echo "Stopping Alto (graceful)..."

# SIGTERM — lets the agent server save sessions before exiting
while IFS= read -r pid; do
  if kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid"
    echo "  SIGTERM → PID $pid"
  fi
done < alto.pid

# Wait up to 10 seconds for clean exit
for i in {1..10}; do
  all_done=true
  while IFS= read -r pid; do
    kill -0 "$pid" 2>/dev/null && all_done=false
  done < alto.pid
  $all_done && break
  sleep 1
done

# Force kill anything still alive
while IFS= read -r pid; do
  if kill -0 "$pid" 2>/dev/null; then
    echo "  SIGKILL → PID $pid"
    kill -9 "$pid" 2>/dev/null
  fi
done < alto.pid

rm -f alto.pid
echo "Stopped."
