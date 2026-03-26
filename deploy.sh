#!/bin/bash
#
# Auto-deploy watcher for Personal Clone.
# Watches for an update trigger from the bot and rebuilds.
#
# Started automatically by start.sh, or manually:
#   chmod +x deploy.sh
#   nohup ./deploy.sh >> data/deploy.log 2>&1 &

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TRIGGER_FILE="$SCRIPT_DIR/data/.update_trigger"
ENV_FILE="$SCRIPT_DIR/data/.env"

read_env_value() {
    # Reads a value from .env, stripping quotes that python-dotenv adds
    local key="$1"
    if [ ! -f "$ENV_FILE" ]; then return 1; fi
    local val=$(grep "^${key}=" "$ENV_FILE" | head -1 | sed "s/^${key}=//")
    # Strip surrounding single or double quotes
    val=$(echo "$val" | sed "s/^['\"]//;s/['\"]$//")
    echo "$val"
}

send_notification() {
    local trigger_content="$1"
    local message="$2"

    local notify_type=$(echo "$trigger_content" | python3 -c "import sys,json; print(json.load(sys.stdin).get('notify',{}).get('type',''))" 2>/dev/null)

    if [ "$notify_type" = "telegram" ]; then
        local chat_id=$(echo "$trigger_content" | python3 -c "import sys,json; print(json.load(sys.stdin)['notify']['chat_id'])" 2>/dev/null)
        local bot_token=$(read_env_value TELEGRAM_BOT_TOKEN)

        if [ -n "$bot_token" ] && [ -n "$chat_id" ]; then
            curl -s -X POST "https://api.telegram.org/bot${bot_token}/sendMessage" \
                -H "Content-Type: application/json" \
                -d "{\"chat_id\": ${chat_id}, \"text\": \"${message}\"}" > /dev/null 2>&1
            echo "  Notification sent to Telegram chat ${chat_id}"
        else
            echo "  WARNING: Could not send Telegram notification (token=${bot_token:+set} chat_id=${chat_id})"
        fi

    elif [ "$notify_type" = "slack" ]; then
        local channel=$(echo "$trigger_content" | python3 -c "import sys,json; print(json.load(sys.stdin)['notify']['channel'])" 2>/dev/null)
        local slack_token=$(read_env_value SLACK_BOT_TOKEN)

        if [ -n "$slack_token" ] && [ -n "$channel" ]; then
            curl -s -X POST "https://slack.com/api/chat.postMessage" \
                -H "Authorization: Bearer ${slack_token}" \
                -H "Content-Type: application/json" \
                -d "{\"channel\": \"${channel}\", \"text\": \"${message}\"}" > /dev/null 2>&1
            echo "  Notification sent to Slack channel ${channel}"
        else
            echo "  WARNING: Could not send Slack notification"
        fi
    else
        echo "  WARNING: No notification channel in trigger file"
    fi
}

wait_for_healthy() {
    echo "  Waiting for container to be healthy..."
    for i in $(seq 1 60); do
        if docker exec personal-clone-agent python3 -c 'import urllib.request; urllib.request.urlopen("http://localhost:8080/health")' > /dev/null 2>&1; then
            echo "  Container is healthy."
            return 0
        fi
        sleep 2
    done
    echo "  WARNING: Container did not become healthy within 120s"
    return 1
}

rollback() {
    local previous_commit="$1"
    local trigger_content="$2"

    echo "  Rolling back to $previous_commit..."
    git reset --hard "$previous_commit"
    chmod +x "$SCRIPT_DIR/start.sh" "$SCRIPT_DIR/deploy.sh" "$SCRIPT_DIR/rollback.sh"
    docker compose build 2>&1
    docker compose up -d 2>&1

    if wait_for_healthy; then
        echo "$(date): Rollback successful."
        send_notification "$trigger_content" "Rollback successful. The previous stable version is now running."
    else
        echo "$(date): ROLLBACK FAILED. Manual intervention required."
        send_notification "$trigger_content" "FATAL: Rollback also failed. The bot is likely offline. Manual intervention required on the server."
    fi
}

echo "$(date): Deploy watcher started. Watching for $TRIGGER_FILE"

while true; do
    if [ -f "$TRIGGER_FILE" ]; then
        echo ""
        echo "$(date): Update triggered, starting deploy..."

        TRIGGER_CONTENT=$(cat "$TRIGGER_FILE")
        rm -f "$TRIGGER_FILE"

        # Give the agent time to send its response before we restart the container
        sleep 10

        cd "$SCRIPT_DIR"

        # Step 0: Save CURRENT commit for potential rollback
        PREVIOUS_COMMIT=$(git rev-parse HEAD)
        echo "  Current stable commit: $PREVIOUS_COMMIT"

        # Step 1: Pull latest from master (Discarding local drift)
        echo "  Fetching latest code and discarding local changes..."
        git fetch origin master 2>&1
        GIT_OUTPUT=$(git reset --hard origin/master 2>&1)
        GIT_STATUS=$?
        echo "  $GIT_OUTPUT"

        # Ensure scripts remain executable after reset
        chmod +x "$SCRIPT_DIR/start.sh" "$SCRIPT_DIR/deploy.sh" "$SCRIPT_DIR/rollback.sh"

        if [ $GIT_STATUS -ne 0 ]; then
            echo "$(date): Update failed (reset error)."
            send_notification "$TRIGGER_CONTENT" "Update failed: git reset error. Check deploy.log on the server."
            echo "---"
            continue
        fi

        if [ "$PREVIOUS_COMMIT" = "$(git rev-parse HEAD)" ]; then
            echo "$(date): No changes to deploy (already at latest commit)."
            echo "---"
            continue
        fi

        # Step 2: Build the new image FIRST
        echo "  Building new image..."
        if ! docker compose build 2>&1; then
            echo "$(date): Docker build failed. Rolling back..."
            send_notification "$TRIGGER_CONTENT" "Update failed: Docker build error. Rolling back to previous version..."
            rollback "$PREVIOUS_COMMIT" "$TRIGGER_CONTENT"
            echo "---"
            continue
        fi

        # Step 3: Swap to new image
        echo "  Swapping to new container..."
        if ! docker compose up -d 2>&1; then
            echo "$(date): docker compose up failed. Rolling back..."
            send_notification "$TRIGGER_CONTENT" "Update failed: container failed to start. Rolling back to previous version..."
            rollback "$PREVIOUS_COMMIT" "$TRIGGER_CONTENT"
            echo "---"
            continue
        fi

        # Step 4: Wait for health check
        if wait_for_healthy; then
            echo "$(date): Deploy complete."
            send_notification "$TRIGGER_CONTENT" "Update complete. I'm back online with the latest changes."
        else
            echo "$(date): Deploy failed health check. ROLLING BACK..."
            send_notification "$TRIGGER_CONTENT" "CRITICAL: Update failed health check. Rolling back to previous stable version..."
            rollback "$PREVIOUS_COMMIT" "$TRIGGER_CONTENT"
        fi

        echo "---"
    fi
    sleep 5
done
