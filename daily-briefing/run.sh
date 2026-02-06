#!/bin/bash
# Daily GTM Briefing Runner
# Runs the full pipeline: crawl → analyze → generate briefing → send

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEMANTIC_GTM_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$SCRIPT_DIR/logs/$(date +%Y-%m-%d).log"

mkdir -p "$SCRIPT_DIR/logs"
mkdir -p "$SCRIPT_DIR/archive"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "======================================"
echo "Daily GTM Briefing - $(date)"
echo "======================================"

cd "$SEMANTIC_GTM_DIR"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Step 1: Crawl new signals
echo ""
echo "Step 1: Crawling new signals..."
python main.py crawl 2>/dev/null || echo "Crawl step skipped (may need setup)"

# Step 2: Analyze with AI (if API key available)
if [ -n "$ANTHROPIC_API_KEY" ] || [ -n "$OPENAI_API_KEY" ]; then
    echo ""
    echo "Step 2: Analyzing signals with AI..."
    python main.py analyze 2>/dev/null || echo "Analysis step skipped"
else
    echo ""
    echo "Step 2: Skipping AI analysis (no API key)"
fi

# Step 3: Generate briefing
echo ""
echo "Step 3: Generating daily briefing..."
cd "$SCRIPT_DIR"
python generate.py "$@"

echo ""
echo "======================================"
echo "Complete - $(date)"
echo "======================================"
