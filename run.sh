#!/usr/bin/env bash
# One-command launch: Temporal dev server + worker + web app.
# Opens both the Temporal Web UI (localhost:8233) and the application form
# (localhost:8000) automatically. Fill out the form to trigger the workflow,
# then watch it execute in the Web UI tab.
#
# For the crash-recovery demo, kill *just* the worker (PID printed below),
# then restart it on its own with: .venv/bin/python -m program_demo.worker
# Ctrl+C here stops everything (dev server, worker, web app).

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

VENV_PY=".venv/bin/python"
VENV_UVICORN=".venv/bin/uvicorn"

if [ ! -x "$VENV_PY" ]; then
  echo "No .venv found. Set up first:"
  echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -e ."
  exit 1
fi

if ! command -v temporal >/dev/null 2>&1; then
  echo "Temporal CLI not found. Install it with: brew install temporal"
  exit 1
fi

if [ ! -f .env ]; then
  echo "No .env found — copy .env.example to .env and add your RESEND_API_KEY first."
  exit 1
fi

mkdir -p .run
SERVER_LOG=.run/server.log
WORKER_LOG=.run/worker.log

wait_for_port() {
  local port=$1
  for _ in $(seq 1 30); do
    if (exec 3<>"/dev/tcp/localhost/$port") 2>/dev/null; then
      exec 3>&- 3<&- 2>/dev/null || true
      return 0
    fi
    sleep 1
  done
  return 1
}

echo "Starting Temporal dev server..."
temporal server start-dev >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$WORKER_PID" 2>/dev/null || true
  kill "$SERVER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if ! wait_for_port 7233; then
  echo "Temporal server didn't come up — check $SERVER_LOG"
  exit 1
fi

echo "Starting worker..."
"$VENV_PY" -m program_demo.worker >"$WORKER_LOG" 2>&1 &
WORKER_PID=$!
echo "Worker PID: $WORKER_PID (log: $WORKER_LOG)"
echo "  crash-recovery demo: kill -9 $WORKER_PID"
echo "  then restart it alone with: $VENV_PY -m program_demo.worker"
echo ""
echo "Temporal Web UI:  http://localhost:8233"
echo "Application form: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop everything."
echo ""

open "http://localhost:8233" >/dev/null 2>&1 || true
open "http://localhost:8000" >/dev/null 2>&1 || true

"$VENV_UVICORN" program_demo.web:app --host 0.0.0.0 --port 8000
