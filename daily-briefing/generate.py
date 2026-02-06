#!/usr/bin/env python3
"""
Daily GTM Briefing Generator

Produces a daily briefing with decaying memory:
- Today/Yesterday: Full detail
- This week: Key highlights
- Last week: Major themes only
- Older: Patterns and trends

Integrates:
- Semantic GTM signals (HN/Reddit/Twitter)
- Market analysis
- GTM actions and follow-ups
- QMD knowledge base queries
"""

import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Paths
SEMANTIC_GTM_DIR = Path("/home/daaronch/semantic-gtm")
GTM_SYSTEM_DIR = Path("/home/daaronch/.openclaw/workspace/gtm-system")
BRIEFING_DIR = SEMANTIC_GTM_DIR / "daily-briefing"
BRIEFINGS_ARCHIVE = BRIEFING_DIR / "archive"

# Ensure directories exist
BRIEFINGS_ARCHIVE.mkdir(parents=True, exist_ok=True)

def get_decay_weight(days_ago: int) -> float:
    """Return importance weight based on recency"""
    if days_ago == 0:
        return 1.0
    elif days_ago == 1:
        return 0.8
    elif days_ago <= 3:
        return 0.5
    elif days_ago <= 7:
        return 0.3
    elif days_ago <= 14:
        return 0.1
    else:
        return 0.05

def get_signals_by_period(db_path: Path, days: int = 14) -> dict:
    """Get signals grouped by time period with decay weighting"""
    if not db_path.exists():
        return {"today": [], "yesterday": [], "this_week": [], "last_week": []}
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    today = datetime.now().date()
    
    periods = {
        "today": [],
        "yesterday": [],
        "this_week": [],
        "last_week": [],
        "older": []
    }
    
    try:
        cursor.execute("""
            SELECT p.*, a.fit_score, a.urgency_score, a.use_case, a.reasoning
            FROM posts p
            LEFT JOIN analysis a ON p.id = a.post_id
            WHERE p.created_at > datetime('now', '-14 days')
            ORDER BY COALESCE(a.fit_score, 0) DESC, p.created_at DESC
        """)
        
        for row in cursor.fetchall():
            created = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')).date()
            days_ago = (today - created).days
            
            signal = {
                "title": row['title'],
                "url": row['url'],
                "source": row['source'],
                "fit_score": row['fit_score'] or 0,
                "urgency_score": row['urgency_score'] or 0,
                "use_case": row['use_case'],
                "reasoning": row['reasoning'],
                "weight": get_decay_weight(days_ago)
            }
            
            if days_ago == 0:
                periods["today"].append(signal)
            elif days_ago == 1:
                periods["yesterday"].append(signal)
            elif days_ago <= 7:
                periods["this_week"].append(signal)
            elif days_ago <= 14:
                periods["last_week"].append(signal)
            else:
                periods["older"].append(signal)
    except sqlite3.OperationalError:
        pass  # Table doesn't exist yet
    
    conn.close()
    return periods

def get_follow_ups(db_path: Path) -> list:
    """Get pending follow-ups from GTM system"""
    if not db_path.exists():
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    follow_ups = []
    try:
        cursor.execute("""
            SELECT * FROM reminders 
            WHERE due_date <= date('now', '+3 days')
            AND completed = 0
            ORDER BY due_date
        """)
        follow_ups = [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        pass
    
    conn.close()
    return follow_ups

def get_pipeline_status(db_path: Path) -> dict:
    """Get current pipeline status from GTM system"""
    if not db_path.exists():
        return {}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    status = {}
    try:
        cursor.execute("""
            SELECT stage, COUNT(*) as count 
            FROM opportunities 
            GROUP BY stage
        """)
        status = {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        pass
    
    conn.close()
    return status

def query_qmd(query: str) -> str:
    """Query QMD knowledge base"""
    try:
        result = subprocess.run(
            ["qmd", "query", query, "-n", "3", "--md"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""

def get_previous_briefings(days: int = 7) -> list:
    """Get summaries from previous briefings"""
    briefings = []
    for i in range(1, days + 1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        path = BRIEFINGS_ARCHIVE / f"{date}.md"
        if path.exists():
            content = path.read_text()
            # Extract just the summary section
            if "## Summary" in content:
                summary = content.split("## Summary")[1].split("##")[0].strip()
                briefings.append({"date": date, "summary": summary[:500]})
    return briefings

def generate_briefing_with_ai(context: dict) -> str:
    """Use AI to generate the briefing"""
    
    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        # Fallback to template-based briefing
        return generate_template_briefing(context)
    
    prompt = f"""Generate a concise daily GTM briefing for Expanso based on this context:

## Signals Found
Today: {len(context['signals']['today'])} new signals
Yesterday: {len(context['signals']['yesterday'])} signals
This Week: {len(context['signals']['this_week'])} signals

Top signals (by fit score):
{json.dumps(context['signals']['today'][:5], indent=2)}

## Follow-ups Due
{json.dumps(context['follow_ups'][:5], indent=2)}

## Pipeline Status
{json.dumps(context['pipeline'], indent=2)}

## Previous Days Context (decaying importance)
{json.dumps(context['previous_briefings'][:3], indent=2)}

## Market Position Reminder
- Primary target: Snowflake/Databricks customers with cost pain
- Key message: "Cut data platform costs in half. Filter at source."
- Closest competitor: Cribl (observability focus, we're broader)

Generate a briefing with:
1. 🎯 Top 3 Priorities Today (specific, actionable)
2. 📊 Signals Worth Acting On (from today's crawl)
3. 🔄 Follow-ups Due
4. 💡 Pattern/Insight (what are we learning?)
5. 📈 One Metric to Watch

Keep it under 500 words. Be specific and actionable."""

    if os.environ.get("ANTHROPIC_API_KEY"):
        return call_anthropic(prompt)
    else:
        return call_openai(prompt)

def call_anthropic(prompt: str) -> str:
    """Call Anthropic API"""
    import urllib.request
    import urllib.error
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    data = json.dumps({
        "model": "claude-3-haiku-20240307",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return result["content"][0]["text"]
    except Exception as e:
        return f"Error generating AI briefing: {e}"

def call_openai(prompt: str) -> str:
    """Call OpenAI API"""
    import urllib.request
    
    api_key = os.environ.get("OPENAI_API_KEY")
    
    data = json.dumps({
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024
    }).encode()
    
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error generating AI briefing: {e}"

def generate_template_briefing(context: dict) -> str:
    """Fallback template-based briefing"""
    today = datetime.now().strftime("%B %d, %Y")
    
    signals = context['signals']
    top_today = signals['today'][:3]
    
    briefing = f"""# Daily GTM Briefing
*{today}*

## 🎯 Top Priorities Today

1. **Review {len(signals['today'])} new signals** from overnight crawl
2. **Follow up** on {len(context['follow_ups'])} pending items
3. **Post in r/dataengineering** about Snowflake cost reduction

## 📊 Top Signals Worth Acting On

"""
    
    for i, signal in enumerate(top_today, 1):
        briefing += f"{i}. **{signal.get('title', 'Untitled')[:60]}**\n"
        briefing += f"   - Fit: {signal.get('fit_score', 'N/A')}/10 | Urgency: {signal.get('urgency_score', 'N/A')}/10\n"
        briefing += f"   - Use case: {signal.get('use_case', 'Unknown')}\n"
        briefing += f"   - URL: {signal.get('url', 'N/A')}\n\n"
    
    if context['follow_ups']:
        briefing += "## 🔄 Follow-ups Due\n\n"
        for fu in context['follow_ups'][:3]:
            briefing += f"- {fu.get('description', 'No description')} (Due: {fu.get('due_date', 'N/A')})\n"
    
    briefing += f"""

## 💡 Key Reminder

**Target:** Snowflake/Databricks customers with cost pain
**Message:** "Cut data platform costs in half. Filter at source."
**Differentiator:** We're not replacing Snowflake—we're making it 50% cheaper.

## 📈 Metric to Watch

Total signals with fit score > 7: {len([s for s in signals['today'] + signals['yesterday'] if s.get('fit_score', 0) >= 7])}

---
*Generated by semantic-gtm daily briefing system*
"""
    
    return briefing

def send_to_telegram(message: str, chat_id: str = "775397536") -> bool:
    """Send briefing to Telegram via OpenClaw"""
    # Write to temp file and let OpenClaw handle it
    temp_path = BRIEFING_DIR / "latest.md"
    temp_path.write_text(message)
    
    # Try to send via OpenClaw message tool
    try:
        subprocess.run([
            "openclaw", "message", "send",
            "--channel", "telegram",
            "--to", chat_id,
            "--message", message[:4000]  # Telegram limit
        ], timeout=30, capture_output=True)
        return True
    except Exception:
        return False

def main():
    print(f"Generating daily briefing for {datetime.now().strftime('%Y-%m-%d')}")
    
    # Gather context
    context = {
        "signals": get_signals_by_period(SEMANTIC_GTM_DIR / "data" / "gtm.db"),
        "follow_ups": get_follow_ups(GTM_SYSTEM_DIR / "data" / "gtm.db"),
        "pipeline": get_pipeline_status(GTM_SYSTEM_DIR / "data" / "gtm.db"),
        "previous_briefings": get_previous_briefings(7)
    }
    
    # Generate briefing
    briefing = generate_briefing_with_ai(context)
    
    # Save to archive
    today = datetime.now().strftime("%Y-%m-%d")
    archive_path = BRIEFINGS_ARCHIVE / f"{today}.md"
    archive_path.write_text(briefing)
    print(f"Saved to {archive_path}")
    
    # Save as latest
    latest_path = BRIEFING_DIR / "latest.md"
    latest_path.write_text(briefing)
    
    # Print briefing
    print("\n" + "="*60)
    print(briefing)
    print("="*60)
    
    # Send to Telegram if requested
    if "--send" in sys.argv:
        if send_to_telegram(briefing):
            print("\n✓ Sent to Telegram")
        else:
            print("\n✗ Failed to send to Telegram")
    
    return briefing

if __name__ == "__main__":
    main()
