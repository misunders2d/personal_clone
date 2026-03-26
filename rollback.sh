#!/bin/bash
#
# Rollback watcher for Personal Clone.
# Watches for a rollback trigger from the bot.
#
# Started automatically by start.sh, or manually:
#   chmod +x rollback.sh
#   nohup ./rollback.sh >> data/rollback.log 2>&1 &

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TRIGGER_FILE="$SCRIPT_DIR/data/.rollback_trigger"
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
        fi
    fi
}

echo "$(date): Rollback watcher started. Watching for $TRIGGER_FILE"

while true; do
    if [ -f "$TRIGGER_FILE" ]; then
        echo ""
        echo "$(date): Rollback triggered, starting process..."

        TRIGGER_CONTENT=$(cat "$TRIGGER_FILE")
        rm -f "$TRIGGER_FILE"

        # Give the agent time to send its response before we restart the container
        sleep 5

        cd "$SCRIPT_DIR"

        CURRENT_COMMIT=$(git rev-parse HEAD)
        echo "  Rolling back from $CURRENT_COMMIT..."

        # Step 1: Git reset HEAD~1
        git reset --hard HEAD~1 2>&1
        NEW_COMMIT=$(git rev-parse HEAD)
        echo "  Now at commit: $NEW_COMMIT"

        # Step 2: Relaunch via start.sh --no-sync
        chmod +x "$SCRIPT_DIR/start.sh"
        ./start.sh --no-sync

        # Notification is handled by curl here since the bot might be coming back up
        send_notification "$TRIGGER_CONTENT" "Rollback complete. Reset to previous commit and restarted. Current commit: $NEW_COMMIT"

        echo "---"
    fi
    sleep 5
done
