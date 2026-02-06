#!/usr/bin/env python3
"""Main orchestration for GTM Semantic Crawler

Usage:
    python main.py crawl      # Crawl all sources
    python main.py analyze    # Run AI analysis
    python main.py digest     # Generate and send daily digest
    python main.py full       # Full pipeline: crawl + analyze + digest
    python main.py query ...  # Query opportunities (pass to CLI)
"""
import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime
from db import init_db, get_stats
from config.settings import TELEGRAM_USER_ID

def run_crawl(days_back: int = 1):
    """Run all crawlers"""
    from crawlers import crawl_hn, crawl_reddit
    
    print(f"[{datetime.now()}] Starting crawl (days_back={days_back})")
    
    print("Crawling Hacker News...")
    hn_stats = crawl_hn(days_back=days_back)
    print(f"  HN: {hn_stats}")
    
    print("Crawling Reddit...")
    reddit_stats = crawl_reddit(days_back=days_back)
    print(f"  Reddit: {reddit_stats}")
    
    return {"hn": hn_stats, "reddit": reddit_stats}

def run_analysis(batch_size: int = 100):
    """Run AI analysis on unanalyzed posts"""
    from analysis import run_analysis as analyze
    
    print(f"[{datetime.now()}] Running analysis (batch_size={batch_size})")
    stats = analyze(batch_size=batch_size)
    print(f"  Analysis: {stats}")
    return stats

def run_digest(send_telegram: bool = True):
    """Generate and optionally send daily digest"""
    from digest import generate_digest, save_digest, format_for_telegram
    
    print(f"[{datetime.now()}] Generating digest")
    digest, meta = generate_digest(days=1)
    
    print("Saving digest to database...")
    save_digest(digest, meta)
    
    print("\n" + "="*50)
    print(digest)
    print("="*50 + "\n")
    
    if send_telegram:
        telegram_text = format_for_telegram(digest)
        print(f"Digest ready for Telegram user {TELEGRAM_USER_ID}")
        # Return the formatted text for sending
        return telegram_text
    
    return digest

def run_full_pipeline(days_back: int = 1, batch_size: int = 100, send_telegram: bool = True):
    """Run full pipeline: crawl -> analyze -> digest"""
    print(f"[{datetime.now()}] Starting full pipeline")
    
    # Initialize DB
    init_db()
    
    # Crawl
    crawl_stats = run_crawl(days_back=days_back)
    
    # Analyze
    analysis_stats = run_analysis(batch_size=batch_size)
    
    # Digest
    digest = run_digest(send_telegram=send_telegram)
    
    # Summary
    db_stats = get_stats()
    print(f"\n[{datetime.now()}] Pipeline complete")
    print(f"  Total posts: {db_stats.get('total_posts', 0)}")
    print(f"  Total analyzed: {db_stats.get('analyzed_posts', 0)}")
    print(f"  High-fit opportunities: {db_stats.get('high_fit_opportunities', 0)}")
    
    return {
        "crawl": crawl_stats,
        "analysis": analysis_stats,
        "stats": db_stats,
        "digest": digest,
    }

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Initialize DB for all commands
    init_db()
    
    if command == "crawl":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        run_crawl(days_back=days)
    
    elif command == "analyze":
        batch = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        run_analysis(batch_size=batch)
    
    elif command == "digest":
        run_digest(send_telegram=True)
    
    elif command == "full":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        run_full_pipeline(days_back=days)
    
    elif command == "query":
        # Pass to CLI
        from cli import cli
        sys.argv = sys.argv[1:]  # Remove 'main.py'
        cli()
    
    elif command == "stats":
        stats = get_stats()
        print("\nGTM Semantic Crawler Stats")
        print("="*40)
        print(f"Total posts: {stats.get('total_posts', 0)}")
        print(f"Analyzed: {stats.get('analyzed_posts', 0)}")
        print(f"High-fit (7+): {stats.get('high_fit_opportunities', 0)}")
        print("\nBy source:")
        for src, cnt in stats.get('by_source', {}).items():
            print(f"  {src}: {cnt}")
        print("\nBy use case:")
        for uc, cnt in list(stats.get('by_use_case', {}).items())[:10]:
            print(f"  {uc}: {cnt}")
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
