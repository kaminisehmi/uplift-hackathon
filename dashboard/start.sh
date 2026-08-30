#!/usr/bin/env bash
# Start the UpLift dashboard.
# Usage:  ./dashboard/start.sh [port]   (default port: 7890)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Find Python — prefer .venv, then python3.12, then python3
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
elif command -v python3.12 &>/dev/null; then
  PYTHON="python3.12"
else
  PYTHON="python3"
fi

PORT="${1:-7890}"
export UPLIFT_DASHBOARD_PORT="$PORT"

echo ""
echo "  UpLift Dashboard"
echo "  Python : $PYTHON"
echo "  URL    : http://localhost:$PORT"
echo "  Ctrl-C to stop."
echo ""

cd "$REPO_ROOT"
"$PYTHON" dashboard/server.py
