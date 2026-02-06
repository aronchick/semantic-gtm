#!/bin/bash
# Slow embedding over time - runs at lowest priority
# Can be killed/resumed without losing progress

set -e

LOG_FILE="/home/daaronch/semantic-gtm/qmd-sync/embed.log"
LOCK_FILE="/tmp/qmd-embed.lock"

# Prevent multiple instances
if [ -f "$LOCK_FILE" ]; then
    pid=$(cat "$LOCK_FILE")
    if ps -p "$pid" > /dev/null 2>&1; then
        echo "Embedding already running (PID $pid)"
        exit 0
    fi
fi
echo $$ > "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

echo "[$(date)] Starting slow embed..." | tee -a "$LOG_FILE"

# Run at lowest CPU/IO priority
nice -n 19 ionice -c 3 qmd embed 2>&1 | tee -a "$LOG_FILE"

echo "[$(date)] Embed complete!" | tee -a "$LOG_FILE"
