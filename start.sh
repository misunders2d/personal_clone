#!/bin/bash
#
# Personal Clone — One-command setup & launch
#
# Usage:
#   chmod +x start.sh   (first time only)
#   ./start.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=========================================="
echo "  Personal Clone — Setup & Launch"
echo "=========================================="
echo ""

# --- Check prerequisites ---

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: '$1' is not installed."
        echo "  $2"
        exit 1
    fi
}

check_command docker "Install Docker: https://docs.docker.com/get-docker/"
check_command git "Install git: https://git-scm.com/downloads"

# Check if docker compose works (v2 plugin)
if ! docker compose version &> /dev/null; then
    echo "ERROR: 'docker compose' not available."
    echo "  Install Docker Compose plugin: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if docker is running
if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running, or you don't have permission."
    echo "  Try: sudo systemctl start docker"
    echo "  Or run this script with sudo."
    exit 1
fi

echo "  Prerequisites OK"
echo ""

# --- Sync to latest remote code ---

if [[ "$1" == "--no-sync" ]]; then
    echo "  Skipping sync (running with --no-sync)..."
else
    echo "  Syncing to latest code..."
    git fetch origin master 2>&1
    git reset --hard origin/master 2>&1
fi
chmod +x "$SCRIPT_DIR/start.sh" "$SCRIPT_DIR/deploy.sh" "$SCRIPT_DIR/rollback.sh" "$SCRIPT_DIR/entrypoint.sh" 2>/dev/null || true

# --- First-time setup ---

mkdir -p "$SCRIPT_DIR/data"
# Ensure the directory is writable by the container's non-root user
chmod -R 777 "$SCRIPT_DIR/data" 2>/dev/null || true

# --- Build and start ---

echo "  Building and starting the bot..."
echo ""

docker compose up --build -d

echo ""

# --- Wait for container to be ready ---

echo "  Waiting for the bot to start..."
for i in $(seq 1 30); do
    if docker exec personal-clone-agent python3 -c 'import urllib.request; urllib.request.urlopen("http://localhost:8080/health")' > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

# --- Check if first boot (needs interactive setup) ---

ENV_FILE="$SCRIPT_DIR/data/.env"
if [ ! -f "$ENV_FILE" ] || ! grep -q "GEMINI_API_KEY" "$ENV_FILE" 2>/dev/null; then
    echo ""
    echo "=========================================="
    echo "  First-time setup required"
    echo "=========================================="
    echo ""
    echo "  The bot needs API keys to run."
    echo "  Starting interactive setup..."
    echo ""

    # Stop the detached container and run interactively for setup
    docker compose down
    docker compose run --rm -it personal-clone

    # After setup exits, start in background
    echo ""
    echo "  Starting the bot in background..."
    docker compose up -d
fi

# --- Start deploy and rollback watchers ---

DEPLOY_PID_FILE="$SCRIPT_DIR/data/.deploy_watcher.pid"
ROLLBACK_PID_FILE="$SCRIPT_DIR/data/.rollback_watcher.pid"

# Kill old watchers if running
for PID_FILE in "$DEPLOY_PID_FILE" "$ROLLBACK_PID_FILE"; do
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill "$OLD_PID" 2>/dev/null || true
            sleep 1
        fi
        rm -f "$PID_FILE"
    fi
done

# Start new watchers
chmod +x "$SCRIPT_DIR/deploy.sh" "$SCRIPT_DIR/rollback.sh" 2>/dev/null || true
nohup "$SCRIPT_DIR/deploy.sh" >> "$SCRIPT_DIR/data/deploy.log" 2>&1 &
echo $! > "$DEPLOY_PID_FILE"

nohup "$SCRIPT_DIR/rollback.sh" >> "$SCRIPT_DIR/data/rollback.log" 2>&1 &
echo $! > "$ROLLBACK_PID_FILE"

# --- Done ---

echo ""
echo "=========================================="
echo "  Personal Clone is running"
echo "=========================================="
echo ""
echo "  Bot:           docker logs -f personal-clone-agent"
echo "  Deploy log:    tail -f data/deploy.log"
echo "  Setup wizard:  http://localhost:8080/setup"
echo "  Health check:  curl http://localhost:8080/health"
echo ""
echo "  To stop:       docker compose down"
echo "  To update:     tell the bot \"update\" in chat"
echo ""
