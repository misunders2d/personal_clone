#!/bin/bash
set -e

ENV_FILE="${DOTENV_PATH:-/code/data/.env}"

# First boot: no .env or no GEMINI_API_KEY configured — run interactive setup
if [ ! -f "$ENV_FILE" ] || ! grep -q "GEMINI_API_KEY" "$ENV_FILE" 2>/dev/null; then
    echo ""
    echo "No configuration found. Starting setup wizard..."
    echo ""
    uv run python setup.py
fi

# Start the server
exec uv run uvicorn main:fastapi_app --host 0.0.0.0 --port 8080

