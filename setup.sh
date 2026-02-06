#!/bin/bash
# GTM Semantic Crawler Setup Script

set -e

cd "$(dirname "$0")"

echo "=== GTM Semantic Crawler Setup ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install
echo "Installing dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

# Initialize database
echo "Initializing database..."
python3 -c "from db import init_db; init_db()"

# Check API keys
echo ""
echo "=== API Key Status ==="
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "✓ ANTHROPIC_API_KEY is set"
else
    echo "✗ ANTHROPIC_API_KEY not set"
fi

if [ -n "$OPENAI_API_KEY" ]; then
    echo "✓ OPENAI_API_KEY is set"
else
    echo "✗ OPENAI_API_KEY not set"
fi

if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo ""
    echo "WARNING: No API key set. Analysis will not work."
    echo "Set one of:"
    echo "  export ANTHROPIC_API_KEY='your-key'"
    echo "  export OPENAI_API_KEY='your-key'"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Usage:"
echo "  source venv/bin/activate"
echo "  python main.py crawl      # Crawl HN"
echo "  python main.py analyze    # Run AI analysis"
echo "  python main.py digest     # Generate digest"
echo "  python main.py full       # Full pipeline"
echo ""
echo "CLI tool:"
echo "  ./gtm query --min-fit 7"
echo "  ./gtm stats"
