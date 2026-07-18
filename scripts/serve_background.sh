#!/usr/bin/env bash
# Start the SkillFlow backend detached so it keeps running after you close the terminal.
set -e
cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  echo "No .venv found. Run ./scripts/run_local.sh once first."
  exit 1
fi
source .venv/bin/activate

LOG="$(pwd)/server.log"
PIDFILE="$(pwd)/server.pid"

# Stop any existing instance on port 8000
if lsof -ti:8000 >/dev/null 2>&1; then
  echo "Stopping existing process on :8000…"
  lsof -ti:8000 | xargs kill 2>/dev/null || true
  sleep 1
fi

# nohup + disown => survives terminal/SSH close (SIGHUP ignored, removed from job table)
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$LOG" 2>&1 &
PID=$!
disown "$PID" 2>/dev/null || disown 2>/dev/null || true
echo "$PID" > "$PIDFILE"

sleep 2
echo "SkillFlow backend started (PID $PID) — detached from this terminal."
echo "  Logs:   $LOG"
echo "  Local:  http://127.0.0.1:8000"
echo "  Team:   http://10.0.128.20:8000        (docs: /docs · verify: /verify)"
echo "Stop it with: ./scripts/stop_server.sh"
