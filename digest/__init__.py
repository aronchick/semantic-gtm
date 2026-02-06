"""Daily Digest Generator for GTM Semantic Crawler"""
from datetime import datetime, timedelta
from typing import Tuple
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import get_opportunities, get_category_trends, get_stats, get_connection
from config.settings import TELEGRAM_USER_ID

def generate_digest(days: int = 1) -> Tuple[str, dict]:
    """Generate daily digest content"""
    
    # Get top opportunities
    top_opps = get_opportunities(min_fit=6, days=days, limit=10)
    
    # Get category trends
    trends_7d = get_category_trends(days=7)
    trends_30d = get_category_trends(days=30)
    
    # Get stats
    stats = get_stats()
    
    # Build digest
    lines = []
    lines.append("🎯 **GTM Semantic Digest**")
    lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d')}\n")
    
    # Stats summary
    lines.append("📊 **Stats**")
    lines.append(f"• Total posts: {stats.get('total_posts', 0)}")
    lines.append(f"• Analyzed: {stats.get('analyzed_posts', 0)}")
    lines.append(f"• High-fit opportunities (7+): {stats.get('high_fit_opportunities', 0)}\n")
    
    # Top opportunities
    if top_opps:
        lines.append("🔥 **Top Opportunities**\n")
        for i, opp in enumerate(top_opps[:10], 1):
            fit = opp.get('fit_score', 0)
            urgency = opp.get('urgency_score', 0)
            use_case = opp.get('use_case', 'other')
            summary = (opp.get('problem_summary') or '')[:100]
            url = opp.get('url', '')
            source = opp.get('source', 'unknown')
            
            lines.append(f"**{i}. [{source.upper()}] {use_case}** (fit:{fit}/urg:{urgency})")
            lines.append(f"   {summary}")
            lines.append(f"   {url}\n")
    else:
        lines.append("_No high-fit opportunities found today._\n")
    
    # Category trends
    if trends_7d:
        lines.append("📈 **Category Trends (7 days)**")
        
        # Aggregate
        cat_counts = {}
        for row in trends_7d:
            cat = row['use_case']
            cat_counts[cat] = cat_counts.get(cat, 0) + row['count']
        
        sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
        for cat, count in sorted_cats[:5]:
            lines.append(f"• {cat}: {count} posts")
        lines.append("")
    
    # Detect emerging patterns
    patterns = detect_patterns(trends_7d, trends_30d)
    if patterns:
        lines.append("🚨 **Emerging Patterns**")
        for pattern in patterns:
            lines.append(f"• {pattern}")
        lines.append("")
    
    digest_text = "\n".join(lines)
    
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "opportunities_count": len(top_opps),
        "stats": stats,
    }
    
    return digest_text, metadata

def detect_patterns(trends_7d: list, trends_30d: list) -> list:
    """Detect emerging patterns by comparing recent vs historical trends"""
    patterns = []
    
    if not trends_7d or not trends_30d:
        return patterns
    
    # Aggregate counts by category
    recent = {}
    for row in trends_7d:
        cat = row['use_case']
        recent[cat] = recent.get(cat, 0) + row['count']
    
    historical = {}
    for row in trends_30d:
        cat = row['use_case']
        historical[cat] = historical.get(cat, 0) + row['count']
    
    # Compare - look for categories growing faster than expected
    for cat, recent_count in recent.items():
        hist_count = historical.get(cat, 0)
        if hist_count > 0:
            # 7 days should be ~23% of 30 days
            expected = hist_count * 0.23
            if recent_count > expected * 1.5 and recent_count >= 5:
                increase = int((recent_count / expected - 1) * 100)
                patterns.append(f"📈 **{cat}** is trending (+{increase}% above expected)")
        elif recent_count >= 3:
            patterns.append(f"🆕 **{cat}** is a new emerging category")
    
    return patterns[:5]  # Limit to top 5 patterns

def save_digest(content: str, metadata: dict):
    """Save digest to database"""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO digests (digest_date, content, opportunities_count, new_patterns)
            VALUES (date('now'), ?, ?, ?)
        """, (
            content,
            metadata.get('opportunities_count', 0),
            json.dumps(metadata.get('patterns', [])),
        ))

def format_for_telegram(digest: str) -> str:
    """Format digest for Telegram (convert markdown)"""
    # Telegram uses different markdown
    text = digest
    # Convert **bold** to *bold* for Telegram
    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    return text

if __name__ == "__main__":
    digest, meta = generate_digest(days=1)
    print(digest)
    print(f"\nMetadata: {meta}")
