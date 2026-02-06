"""Reddit crawler using JSON API (no auth needed)"""
import requests
from datetime import datetime, timedelta, timezone
from typing import Generator
import time

from config.settings import REDDIT_SUBREDDITS, REDDIT_USER_AGENT
from db import insert_post

def get_subreddit_posts(subreddit: str, sort: str = "new", 
                        limit: int = 100) -> Generator[dict, None, None]:
    """Get posts from a subreddit using Reddit's JSON API"""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    
    headers = {"User-Agent": REDDIT_USER_AGENT}
    params = {"limit": min(limit, 100)}
    
    after = None
    fetched = 0
    
    while fetched < limit:
        if after:
            params["after"] = after
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"Reddit API error for r/{subreddit}: {e}")
            break
        
        posts = data.get("data", {}).get("children", [])
        if not posts:
            break
        
        for post in posts:
            yield post.get("data", {})
            fetched += 1
        
        after = data.get("data", {}).get("after")
        if not after:
            break
        
        time.sleep(2)  # Reddit rate limiting

def get_post_comments(subreddit: str, post_id: str, 
                      limit: int = 50) -> Generator[dict, None, None]:
    """Get comments for a specific post"""
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
    
    headers = {"User-Agent": REDDIT_USER_AGENT}
    params = {"limit": limit, "depth": 3}
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"Reddit comments API error: {e}")
        return
    
    if len(data) < 2:
        return
    
    def extract_comments(listing):
        """Recursively extract comments"""
        for child in listing.get("data", {}).get("children", []):
            if child.get("kind") != "t1":
                continue
            comment = child.get("data", {})
            yield comment
            
            # Get replies
            replies = comment.get("replies")
            if isinstance(replies, dict):
                yield from extract_comments(replies)
    
    yield from extract_comments(data[1])

def crawl_reddit(days_back: int = 1, include_comments: bool = True) -> dict:
    """Crawl Reddit for relevant posts and comments"""
    since = datetime.now(timezone.utc) - timedelta(days=days_back)
    since_ts = since.timestamp()
    
    stats = {"new": 0, "skipped": 0, "errors": 0}
    
    for subreddit in REDDIT_SUBREDDITS:
        print(f"Crawling r/{subreddit}")
        
        for post in get_subreddit_posts(subreddit, limit=50):
            try:
                created_utc = post.get("created_utc", 0)
                
                # Skip old posts
                if created_utc < since_ts:
                    continue
                
                source_id = post.get("id")
                title = post.get("title", "")
                body = post.get("selftext", "")
                url = f"https://reddit.com{post.get('permalink', '')}"
                
                result = insert_post(
                    source="reddit",
                    source_id=source_id,
                    title=title,
                    body=body,
                    url=url,
                    author=post.get("author"),
                    created_at=datetime.fromtimestamp(created_utc),
                    metadata={
                        "subreddit": subreddit,
                        "score": post.get("score"),
                        "num_comments": post.get("num_comments"),
                        "upvote_ratio": post.get("upvote_ratio"),
                        "type": "post",
                    }
                )
                
                if result:
                    stats["new"] += 1
                else:
                    stats["skipped"] += 1
                
                # Get comments for posts with engagement
                if include_comments and post.get("num_comments", 0) > 5:
                    time.sleep(2)
                    
                    for comment in get_post_comments(subreddit, source_id):
                        try:
                            comment_created = comment.get("created_utc", 0)
                            if comment_created < since_ts:
                                continue
                            
                            comment_result = insert_post(
                                source="reddit",
                                source_id=comment.get("id"),
                                title=title,  # Parent post title
                                body=comment.get("body", ""),
                                url=f"https://reddit.com{comment.get('permalink', '')}",
                                author=comment.get("author"),
                                created_at=datetime.fromtimestamp(comment_created),
                                metadata={
                                    "subreddit": subreddit,
                                    "score": comment.get("score"),
                                    "parent_id": source_id,
                                    "type": "comment",
                                }
                            )
                            
                            if comment_result:
                                stats["new"] += 1
                            else:
                                stats["skipped"] += 1
                                
                        except Exception as e:
                            stats["errors"] += 1
                    
            except Exception as e:
                print(f"Error processing Reddit post: {e}")
                stats["errors"] += 1
        
        time.sleep(3)  # Be nice between subreddits
    
    return stats

if __name__ == "__main__":
    from db import init_db
    init_db()
    stats = crawl_reddit(days_back=1)
    print(f"Reddit crawl complete: {stats}")
