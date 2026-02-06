"""Hacker News crawler using Algolia API"""
import requests
from datetime import datetime, timedelta, timezone
from typing import Generator
import time

from config.settings import HN_API_BASE, HN_SEARCH_TERMS
from db import insert_post

def search_hn(query: str, tags: str = "(story,comment)", 
              created_after: datetime = None) -> Generator[dict, None, None]:
    """Search HN using Algolia API (sorted by date for recent content)"""
    url = f"{HN_API_BASE}/search_by_date"
    
    params = {
        "query": query,
        "tags": tags,
        "hitsPerPage": 100,
    }
    
    if created_after:
        ts = int(created_after.timestamp())
        params["numericFilters"] = f"created_at_i>{ts}"
    
    page = 0
    while True:
        params["page"] = page
        
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"HN API error: {e}")
            break
        
        hits = data.get("hits", [])
        if not hits:
            break
        
        for hit in hits:
            yield hit
        
        if page >= data.get("nbPages", 1) - 1:
            break
        
        page += 1
        time.sleep(0.5)  # Rate limiting

def crawl_hn(days_back: int = 1) -> dict:
    """Crawl HN for relevant posts and comments"""
    since = datetime.now(timezone.utc) - timedelta(days=days_back)
    
    stats = {"new": 0, "skipped": 0, "errors": 0}
    
    for term in HN_SEARCH_TERMS:
        print(f"Searching HN for: {term}")
        
        for hit in search_hn(term, created_after=since):
            try:
                source_id = hit.get("objectID")
                
                # Determine if it's a story or comment
                is_story = hit.get("story_id") is None
                
                title = hit.get("title") or hit.get("story_title")
                body = hit.get("comment_text") or hit.get("story_text") or ""
                
                # Build URL
                if is_story:
                    url = hit.get("url") or f"https://news.ycombinator.com/item?id={source_id}"
                else:
                    url = f"https://news.ycombinator.com/item?id={source_id}"
                
                created_at = datetime.fromtimestamp(hit.get("created_at_i", 0))
                
                result = insert_post(
                    source="hn",
                    source_id=source_id,
                    title=title,
                    body=body,
                    url=url,
                    author=hit.get("author"),
                    created_at=created_at,
                    metadata={
                        "points": hit.get("points"),
                        "num_comments": hit.get("num_comments"),
                        "story_id": hit.get("story_id"),
                        "search_term": term,
                    }
                )
                
                if result:
                    stats["new"] += 1
                else:
                    stats["skipped"] += 1
                    
            except Exception as e:
                print(f"Error processing HN hit: {e}")
                stats["errors"] += 1
        
        time.sleep(1)  # Be nice to the API
    
    return stats

if __name__ == "__main__":
    from db import init_db
    init_db()
    stats = crawl_hn(days_back=7)
    print(f"HN crawl complete: {stats}")
