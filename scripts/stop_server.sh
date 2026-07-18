#!/usr/bin/env bash
# Stop the detached SkillFlow backend.
cd "$(dirname "$0")/.."
PIDFILE="$(pwd)/server.pid"

if [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "Stopped PID $(cat "$PIDFILE")."
  rm -f "$PIDFILE"
elif lsof -ti:8000 >/dev/null 2>&1; then
  lsof -ti:8000 | xargs kill 2>/dev/null && echo "Stopped process on :8000."
  rm -f "$PIDFILE"
else
  echo "Nothing running on :8000."
  rm -f "$PIDFILE"
fi
