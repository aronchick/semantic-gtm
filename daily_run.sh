#!/bin/bash
# Daily GTM Semantic Crawler Run
# Add to cron: 0 6 * * * /path/to/gtm-semantic/daily_run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Set your API keys here or in environment
# export ANTHROPIC_API_KEY="your-key"

# Activate venv
source venv/bin/activate

# Log file
LOG_FILE="logs/daily_$(date +%Y-%m-%d).log"
mkdir -p logs

echo "=== GTM Daily Run $(date) ===" >> "$LOG_FILE"

# Run full pipeline
python main.py full 2>&1 | tee -a "$LOG_FILE"

echo "=== Complete $(date) ===" >> "$LOG_FILE"

# The digest will be printed to stdout
# To send to Telegram, the main agent should pick this up
# Or configure a Telegram bot token and use:
# python -c "
# from digest import generate_digest, format_for_telegram
# digest, _ = generate_digest()
# print(format_for_telegram(digest))
# " | send_to_telegram.sh
