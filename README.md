# GTM Semantic Crawler + PMF Laboratory

AI-powered GTM system that finds opportunities Expanso doesn't know to look for.

## The Problem

- Keyword monitoring only catches known terms
- Expanso is flexible, needs to find the right wedge for PMF
- Need to discover **problems**, not just track mentions

## Solution

This system semantically analyzes posts from HN and Reddit to identify people experiencing problems that Bacalhau/Expanso could solve, even if they never mention those terms.

## Quick Start

```bash
cd /home/daaronch/.openclaw/workspace/gtm-semantic

# Install dependencies
pip install -r requirements.txt

# Set API key (pick one)
export ANTHROPIC_API_KEY="your-key"  # preferred
# or
export OPENAI_API_KEY="your-key"

# Run full pipeline
python main.py full

# Or step by step
python main.py crawl      # Crawl HN + Reddit
python main.py analyze    # Run AI analysis
python main.py digest     # Generate digest
```

## CLI Usage

```bash
# Make CLI executable
chmod +x gtm

# Query opportunities
./gtm query --min-fit 7 --days 7

# Filter by use case
./gtm query -u ml_inference --min-fit 6

# Show stats
./gtm stats

# Show category trends
./gtm trends --days 30

# Export for outreach
./gtm export ml_inference --days 7 --limit 10

# Output as JSON
./gtm query --json-output > opportunities.json
```

## Architecture

```
gtm-semantic/
├── config/
│   └── settings.py      # Configuration, API keys, categories
├── crawlers/
│   ├── hn.py           # Hacker News (Algolia API)
│   └── reddit.py       # Reddit (JSON API)
├── analysis/
│   └── __init__.py     # AI analysis pipeline
├── db/
│   ├── schema.sql      # SQLite schema
│   └── __init__.py     # Database operations
├── cli/
│   └── __init__.py     # Query interface
├── digest/
│   └── __init__.py     # Daily digest generator
├── main.py             # Orchestration
└── gtm                 # CLI entry point
```

## How It Works

### 1. Crawlers
- **HN**: Searches Algolia API for semantic terms (not just keywords) ✅ Works
- **Reddit**: Monitors relevant subreddits (⚠️ requires API credentials - see note below)

### 2. AI Analysis Pipeline
For each post, the LLM answers:
- "Is this person experiencing a problem that edge computing / distributed data processing / Bacalhau could solve?"
- Fit score (0-10)
- Urgency score (0-10)
- Use case category
- Problem summary

Uses Claude Haiku or GPT-4o-mini for cost-effective volume processing.

### 3. Problem Taxonomy
Categories tracked:
- `ml_inference` - ML model deployment/inference at edge
- `data_pipelines` - ETL, data processing workflows
- `iot_edge` - IoT data processing, edge compute
- `batch_processing` - Large-scale batch jobs
- `distributed_compute` - General distributed needs
- `cost_optimization` - Cloud/compute cost reduction
- `latency_sensitive` - Low-latency requirements
- `data_locality` - Processing data where it lives
- `hybrid_cloud` - Multi-cloud infrastructure
- `workflow_orchestration` - Scheduling pain points

### 4. Daily Digest
- Top 10 opportunities by fit/urgency
- Category trends
- Emerging pattern alerts
- Sent to Telegram

## Reddit API Note

Reddit now blocks unauthenticated API requests. To enable Reddit crawling:

1. Create a Reddit app at https://www.reddit.com/prefs/apps
2. Get your client_id and client_secret
3. Set environment variables:
   ```bash
   export REDDIT_CLIENT_ID="your-id"
   export REDDIT_CLIENT_SECRET="your-secret"
   ```

Alternative: Use Pushshift API (if available) or focus on HN for initial PMF research.

## Configuration

Edit `config/settings.py`:

```python
# Model selection
ANALYSIS_MODEL = "claude-3-haiku-20240307"
ANALYSIS_PROVIDER = "anthropic"

# Subreddits to monitor
REDDIT_SUBREDDITS = [
    "dataengineering",
    "MachineLearning",
    "mlops",
    ...
]

# HN search terms
HN_SEARCH_TERMS = [
    "distributed computing",
    "edge computing",
    ...
]
```

## Cron Setup

Add to crontab for daily runs:

```bash
# Run at 6 AM UTC daily
0 6 * * * cd /home/daaronch/.openclaw/workspace/gtm-semantic && python main.py full >> /var/log/gtm-semantic.log 2>&1
```

## Database

SQLite database at `db/gtm_semantic.db`:

```sql
-- Query high-fit opportunities directly
SELECT p.title, p.url, a.fit_score, a.urgency_score, a.problem_summary
FROM posts p
JOIN analysis a ON p.id = a.post_id
WHERE a.fit_score >= 7
ORDER BY a.fit_score DESC, a.urgency_score DESC;
```

## Costs

Using Claude Haiku (~$0.00025 per 1K input tokens):
- ~500 posts/day analyzed
- ~$0.50-1.00/day estimated

## Output Examples

### Query
```
┏━━━━━┳━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Fit ┃ Urg ┃ Use Case        ┃ Source ┃ Summary                        ┃
┡━━━━━╇━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│  9  │  8  │ ml_inference    │ reddit │ Struggling to deploy models... │
│  8  │  7  │ data_pipelines  │ hn     │ Airflow is too complex for...  │
│  8  │  6  │ iot_edge        │ reddit │ Need to process sensor data... │
└─────┴─────┴─────────────────┴────────┴────────────────────────────────┘
```

### Digest
```
🎯 GTM Semantic Digest
📅 2024-02-06

📊 Stats
• Total posts: 1,234
• Analyzed: 890
• High-fit opportunities (7+): 45

🔥 Top Opportunities

1. [REDDIT] ml_inference (fit:9/urg:8)
   User struggling to deploy ML models at edge without cloud round-trip
   https://reddit.com/r/mlops/comments/...

📈 Category Trends (7 days)
• ml_inference: 23 posts
• data_pipelines: 18 posts
• iot_edge: 12 posts

🚨 Emerging Patterns
• 📈 iot_edge is trending (+45% above expected)
```

## This Is Your PMF Laboratory

Use this to:
1. **Discover new use cases** - What problems keep appearing?
2. **Test messaging** - Which problem categories get highest fit scores?
3. **Find wedge opportunities** - Where is urgency highest?
4. **Track market evolution** - Are patterns changing?

The goal isn't just lead gen—it's understanding what problems the market actually has that you can solve.
