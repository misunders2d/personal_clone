#!/bin/bash
set -e

echo "Starting Telegram Interface..."
uv run python interface_tg/tg_bot.py &

echo "Starting Slack Interface..."
uv run python interface_slack/slack_bot.py &

echo "Starting Personal Clone (ADK Web)..."
uv run adk web . --port 8501 --host 0.0.0.0 &

# Wait for any of the background processes to exit
wait -n

echo "A process has exited. Shutting down container..."
exit 1
