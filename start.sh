#!/bin/bash
#
# Personal Clone — Setup & Launch
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

# Check if docker compose works
if ! docker compose version &> /dev/null; then
    echo "ERROR: 'docker compose' not available."
    exit 1
fi

# Check if docker is running
if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running."
    exit 1
fi

echo "  Prerequisites OK"
echo ""

# --- Sync to latest remote code ---

if [[ "$1" == "--no-sync" ]]; then
    echo "  Skipping sync..."
else
    echo "  Syncing to latest code..."
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    echo "  Detected branch: $CURRENT_BRANCH"
    
    # Only sync if on master or if origin/$CURRENT_BRANCH exists
    if git rev-parse --verify "origin/$CURRENT_BRANCH" >/dev/null 2>&1; then
        git fetch origin "$CURRENT_BRANCH" 2>&1
        # BE CAREFUL: This will overwrite local changes!
        # git reset --hard "origin/$CURRENT_BRANCH" 2>&1
        echo "  (Skipping hard reset to avoid wiping local uncommitted work)"
        echo "  (Run with --no-sync to skip this check next time)"
    else
        echo "  Warning: origin/$CURRENT_BRANCH not found. Skipping sync."
    fi
fi

# Ensure scripts remain executable
chmod +x "$SCRIPT_DIR/start.sh" "$SCRIPT_DIR/deploy.sh" "$SCRIPT_DIR/entrypoint.sh" 2>/dev/null || true

# --- First-time setup ---

mkdir -p "$SCRIPT_DIR/data"
chmod -R 777 "$SCRIPT_DIR/data" 2>/dev/null || true

# --- Build and start ---

echo "  Building and starting the bot..."
docker compose up --build -d

echo ""
echo "  Waiting for the bot to start..."
for i in $(seq 1 30); do
    if docker exec personal-clone-agent curl -s http://localhost:8080/health > /dev/null 2>&1; then
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
    echo "  Starting interactive setup..."
    
    docker compose down
    docker compose run --rm -it personal-clone
    
    echo "  Starting in background..."
    docker compose up -d
fi

# --- Start deploy watcher ---

DEPLOY_PID_FILE="$SCRIPT_DIR/data/.deploy_watcher.pid"
if [ -f "$DEPLOY_PID_FILE" ]; then
    OLD_PID=$(cat "$DEPLOY_PID_FILE")
    kill "$OLD_PID" 2>/dev/null || true
    rm -f "$DEPLOY_PID_FILE"
fi

nohup "$SCRIPT_DIR/deploy.sh" >> "$SCRIPT_DIR/data/deploy.log" 2>&1 &
echo $! > "$DEPLOY_PID_FILE"

# --- Done ---

echo ""
echo "=========================================="
echo "  Personal Clone is running"
echo "=========================================="
echo "  Logs:          docker logs -f personal-clone-agent"
echo "  Setup Wizard:  http://localhost:8080/setup"
echo ""
