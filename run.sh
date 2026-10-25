#!/usr/bin/env bash
# ==============================================================================
# Capri Telegram AI Userbot [v1.5.0] - Linux / macOS Launcher
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=============================================================================="
echo "          🌟 CAPRI TELEGRAM AI USERBOT [v1.5.0] - LAUNCHER"
echo "=============================================================================="

# 1. Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ [ERROR] python3 is not installed or not in PATH."
    exit 1
fi

# 2. Virtual Environment
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment (venv)..."
    python3 -m venv venv
fi

source venv/bin/activate

# 3. Dependencies
if ! python -c "import telethon" &>/dev/null; then
    echo "[*] Installing dependencies from requirements.txt..."
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
fi

# 4. Check .env
if [ ! -f ".env" ]; then
    echo "[!] No .env found. Copying from .env.example..."
    cp .env.example .env
    echo "⚠️ Please edit .env with your credentials and re-run ./run.sh."
    exit 1
fi

# 5. Check Telegram session
if [ ! -f "session.session" ] && [ ! -f "session" ]; then
    echo "[*] First-time authentication required. Running login.py..."
    python login.py
fi

# 6. Run Bot
echo "[*] Starting Capri Userbot [v1.5.0]..."
python bot.py
