#!/bin/bash
set -euo pipefail

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:$PATH"

DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_LOG="${TMPDIR:-/tmp}/libertas-backend.log"

# Optional: switch to a branch before starting
if [ "${1:-}" != "" ]; then
  BRANCH="$1"
  CURRENT_BRANCH="$(git -C "$DIR" rev-parse --abbrev-ref HEAD)"
  if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo "Switching to branch: $BRANCH"
    git -C "$DIR" checkout "$BRANCH"
  else
    echo "Already on branch: $BRANCH"
  fi
fi

ensure_backend_env() {
  if [ ! -x "$DIR/.venv/bin/python" ]; then
    if ! command -v uv >/dev/null 2>&1; then
      echo "Error: .venv is missing and 'uv' is not installed."
      echo "Install uv, then re-run ./start.sh"
      exit 1
    fi
    echo "Creating backend virtualenv (.venv)..."
    uv venv --python 3.12 "$DIR/.venv"
  fi

  if ! "$DIR/.venv/bin/python" -c "import fastapi, uvicorn, feedparser" >/dev/null 2>&1; then
    if ! command -v uv >/dev/null 2>&1; then
      echo "Error: backend dependencies are missing and 'uv' is not installed."
      echo "Install backend deps manually: .venv/bin/pip install -r backend/requirements.txt"
      exit 1
    fi
    echo "Installing backend dependencies..."
    uv pip install --python "$DIR/.venv/bin/python" -r "$DIR/backend/requirements.txt"
  fi
}

ensure_frontend_env() {
  if [ ! -x "$DIR/frontend/node_modules/.bin/vite" ]; then
    if ! command -v bun >/dev/null 2>&1; then
      echo "Error: frontend dependencies are missing and 'bun' is not installed."
      echo "Install bun, then run: cd frontend && bun install"
      exit 1
    fi
    echo "Installing frontend dependencies..."
    (cd "$DIR/frontend" && bun install)
  fi
}

if [ ! -f "$DIR/.setup-complete" ]; then
  echo "First run detected — running setup..."
  bash "$DIR/setup.sh"
fi

ensure_backend_env
ensure_frontend_env
UVICORN_CMD=("$DIR/.venv/bin/python" "-m" "uvicorn")

# Start backend first and verify it's reachable.
# Use reload only when explicitly requested because file watching can fail
# on some machines/sandboxes and leave frontend proxying to a dead backend.
if [ "${LIBERTAS_RELOAD:-0}" = "1" ]; then
  BACKEND_ARGS="--reload"
else
  BACKEND_ARGS=""
fi

"${UVICORN_CMD[@]}" backend.main:app --app-dir "$DIR" --host 127.0.0.1 --port 8000 $BACKEND_ARGS >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "${FRONTEND_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT

BACKEND_READY=0
for _ in {1..40}; do
  if curl -fsS "http://127.0.0.1:8000/api/health" >/dev/null 2>&1; then
    BACKEND_READY=1
    break
  fi
  if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    echo "Error: backend failed to start."
    echo "Backend logs:"
    tail -n 80 "$BACKEND_LOG" || true
    exit 1
  fi
  sleep 0.25
done

if [ "$BACKEND_READY" -ne 1 ]; then
  echo "Error: backend did not become healthy at http://127.0.0.1:8000/api/health"
  echo "Backend logs:"
  tail -n 80 "$BACKEND_LOG" || true
  exit 1
fi

# Start frontend
cd "$DIR/frontend"
bun run dev &
FRONTEND_PID=$!

echo ""
echo "  Libertas is running:"
echo "    Backend:  http://127.0.0.1:8000"
echo "    Frontend: http://localhost:5173 (or next available port)"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

wait
