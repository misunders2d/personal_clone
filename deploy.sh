#!/bin/bash
#
# Auto-deploy watcher for Personal Clone.
# Watches for an update trigger from the bot and rebuilds.
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TRIGGER_FILE="$SCRIPT_DIR/data/.update_trigger"
ENV_FILE="$SCRIPT_DIR/data/.env"

read_env_value() {
    local key="$1"
    if [ ! -f "$ENV_FILE" ]; then return 1; fi
    local val=$(grep "^${key}=" "$ENV_FILE" | head -1 | sed "s/^${key}=//")
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
                -d "{\"chat_id\": \"${chat_id}\", \"text\": \"${message}\"}" > /dev/null 2>&1
        fi
    elif [ "$notify_type" = "slack" ]; then
        local channel=$(echo "$trigger_content" | python3 -c "import sys,json; print(json.load(sys.stdin)['notify']['channel'])" 2>/dev/null)
        local slack_token=$(read_env_value SLACK_BOT_TOKEN)
        if [ -n "$slack_token" ] && [ -n "$channel" ]; then
            curl -s -X POST "https://slack.com/api/chat.postMessage" \
                -H "Authorization: Bearer ${slack_token}" \
                -H "Content-Type: application/json" \
                -d "{\"channel\": \"${channel}\", \"text\": \"${message}\"}" > /dev/null 2>&1
        fi
    fi
}

wait_for_healthy() {
    echo "  Waiting for container to be healthy..."
    for i in $(seq 1 60); do
        if docker exec personal-clone-agent curl -s http://localhost:8080/health > /dev/null 2>&1; then
            echo "  Container is healthy."
            return 0
        fi
        sleep 2
    done
    return 1
}

rollback() {
    local previous_commit="$1"
    local trigger_content="$2"

    echo "  Rolling back to $previous_commit..."
    git reset --hard "$previous_commit"
    chmod +x "$SCRIPT_DIR/start.sh" "$SCRIPT_DIR/deploy.sh"
    docker compose build 2>&1
    docker compose up -d 2>&1

    if wait_for_healthy; then
        echo "$(date): Rollback successful."
        send_notification "$trigger_content" "✅ Rollback successful. Previous stable version restored."
    else
        echo "$(date): ROLLBACK FAILED. Manual intervention required."
        send_notification "$trigger_content" "🚨 FATAL: Rollback failed. Manual intervention required."
    fi
}

echo "$(date): Deploy watcher started. Watching for $TRIGGER_FILE"

while true; do
    if [ -f "$TRIGGER_FILE" ]; then
        echo ""
        echo "$(date): Update triggered, starting deploy..."

        TRIGGER_CONTENT=$(cat "$TRIGGER_FILE")
        rm -f "$TRIGGER_FILE"

        sleep 10
        cd "$SCRIPT_DIR"

        PREVIOUS_COMMIT=$(git rev-parse HEAD)
        echo "  Current stable commit: $PREVIOUS_COMMIT"

        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
        git fetch origin "$CURRENT_BRANCH" 2>&1
        GIT_OUTPUT=$(git reset --hard "origin/$CURRENT_BRANCH" 2>&1)
        GIT_STATUS=$?
        echo "  $GIT_OUTPUT"

        chmod +x "$SCRIPT_DIR/start.sh" "$SCRIPT_DIR/deploy.sh"

        if [ $GIT_STATUS -ne 0 ]; then
            echo "$(date): Update failed (reset error)."
            send_notification "$TRIGGER_CONTENT" "Update failed: git reset error."
            continue
        fi

        if [ "$PREVIOUS_COMMIT" = "$(git rev-parse HEAD)" ]; then
            echo "$(date): No changes to deploy."
            continue
        fi

        if ! docker compose build 2>&1; then
            echo "$(date): Docker build failed. Rolling back..."
            send_notification "$TRIGGER_CONTENT" "⚠️ Update failed: Docker build error. Rolling back..."
            rollback "$PREVIOUS_COMMIT" "$TRIGGER_CONTENT"
            continue
        fi

        if ! docker compose up -d 2>&1; then
            echo "$(date): docker compose up failed. Rolling back..."
            send_notification "$TRIGGER_CONTENT" "⚠️ Update failed: container failed to start. Rolling back..."
            rollback "$PREVIOUS_COMMIT" "$TRIGGER_CONTENT"
            continue
        fi

        if wait_for_healthy; then
            echo "$(date): Deploy complete."
            send_notification "$TRIGGER_CONTENT" "Update complete. I'm back online."
        else
            echo "$(date): Deploy failed health check. ROLLING BACK..."
            send_notification "$TRIGGER_CONTENT" "⚠️ Update failed health check. Rolling back..."
            rollback "$PREVIOUS_COMMIT" "$TRIGGER_CONTENT"
        fi
        echo "---"
    fi
    sleep 5
done
