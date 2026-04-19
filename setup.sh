#!/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
MARKER="$DIR/.setup-complete"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $*"; }
info() { echo -e "${YELLOW}→${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; exit 1; }
header() { echo -e "\n${BOLD}$*${NC}"; }

echo ""
echo -e "${BOLD}Libertas Setup${NC}"
echo "────────────────────────────────────"

# ── 1. Check uv ──────────────────────────────────────────────────────────────
header "1. Checking uv (Python package manager)"
if command -v uv >/dev/null 2>&1; then
  ok "uv $(uv --version | head -1)"
else
  fail "uv not found. Install it with:
    curl -LsSf https://astral.sh/uv/install.sh | sh
  Then re-run ./setup.sh"
fi

# ── 2. Check bun ─────────────────────────────────────────────────────────────
header "2. Checking bun (JavaScript runtime)"
if command -v bun >/dev/null 2>&1; then
  ok "bun $(bun --version)"
else
  fail "bun not found. Install it with:
    curl -fsSL https://bun.sh/install | bash
  Then re-run ./setup.sh"
fi

# ── 3. Backend virtualenv ─────────────────────────────────────────────────────
header "3. Setting up Python virtualenv"
if [ ! -x "$DIR/.venv/bin/python" ]; then
  info "Creating .venv with Python 3.12..."
  uv venv --python 3.12 "$DIR/.venv"
  ok "Virtualenv created"
else
  ok "Virtualenv already exists"
fi

# ── 4. Backend dependencies ───────────────────────────────────────────────────
header "4. Installing backend dependencies"
if ! "$DIR/.venv/bin/python" -c "import fastapi, uvicorn, feedparser" >/dev/null 2>&1; then
  info "Installing from backend/requirements.txt..."
  uv pip install --python "$DIR/.venv/bin/python" -r "$DIR/backend/requirements.txt"
  ok "Backend dependencies installed"
else
  ok "Backend dependencies already installed"
fi

# ── 5. Frontend dependencies ──────────────────────────────────────────────────
header "5. Installing frontend dependencies"
if [ ! -x "$DIR/frontend/node_modules/.bin/vite" ]; then
  info "Running bun install in frontend/..."
  (cd "$DIR/frontend" && bun install)
  ok "Frontend dependencies installed"
else
  ok "Frontend dependencies already installed"
fi

# ── 6. Data directories ───────────────────────────────────────────────────────
header "6. Creating data directories"
mkdir -p "$DIR/data/watch" "$DIR/data/backups"
ok "data/, data/watch/, data/backups/ ready"

# ── 7. Mark setup complete ────────────────────────────────────────────────────
touch "$MARKER"

echo ""
echo -e "${BOLD}────────────────────────────────────${NC}"
echo -e "${GREEN}${BOLD}Setup complete!${NC}"
echo ""
echo "  Run the app:   ${BOLD}./start.sh${NC}"
echo "  View docs:     ${BOLD}./start-docs.sh${NC}"
echo ""
