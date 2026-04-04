#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
source "$DIR/.venv/bin/activate"

# Start backend
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend
cd "$DIR/frontend"
bun run dev &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

echo ""
echo "  Libertas is running:"
echo "    Backend:  http://localhost:8000"
echo "    Frontend: http://localhost:5173"
echo ""
echo "  Press Ctrl+C to stop."
echo ""

wait
