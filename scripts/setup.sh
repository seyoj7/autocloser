#!/bin/bash
# AutoCloser — One-time setup script
# Creates venv, installs dependencies, and installs Playwright Chromium.
# Safe to re-run — skips steps that are already done.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
echo "[SETUP] Project root: $PROJECT_DIR"

# Create venv if missing
if [ ! -d "venv" ]; then
    echo "[SETUP] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[SETUP] venv already exists, skipping."
fi

# Activate and install deps
source venv/bin/activate
echo "[SETUP] Installing Python packages..."
pip install -q -r requirements.txt

# Install Playwright Chromium
echo "[SETUP] Installing Playwright Chromium..."
python -m playwright install chromium 2>/dev/null || true

echo ""
echo "[SETUP] ✅ Setup complete! AutoCloser is ready to run."
echo "[SETUP] Run: cd $PROJECT_DIR && source venv/bin/activate && python3 scripts/main.py --single-cycle --no-input"
