#!/usr/bin/env bash

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_ACTIVATE="$SCRIPT_DIR/env/bin/activate"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
MAIN="$SCRIPT_DIR/main.py"

# ── Activate virtual environment ──────────────────────────────────────────────
if [[ ! -f "$VENV_ACTIVATE" ]]; then
    echo "[ERROR] Virtual environment not found at: $VENV_ACTIVATE" >&2
    exit 1
fi

echo "[INFO] Activating virtual environment..."
source "$VENV_ACTIVATE"

# ── Install / sync dependencies ───────────────────────────────────────────────
if [[ ! -f "$REQUIREMENTS" ]]; then
    echo "[ERROR] requirements.txt not found at: $REQUIREMENTS" >&2
    exit 1
fi

echo "[INFO] Installing packages from requirements.txt..."
pip install --quiet -r "$REQUIREMENTS"

# ── Launch application ────────────────────────────────────────────────────────
echo "[INFO] Starting main.py with Python: $(which python) ($(python --version))"
exec python "$MAIN" --start-checker
