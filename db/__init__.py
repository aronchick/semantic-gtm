"""Database module for GTM Semantic Crawler"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

from config.settings import DB_PATH

def init_db():
    """Initialize database with schema"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path) as f:
        schema = f.read()
    
    with get_connection() as conn:
        conn.executescript(schema)
    
    return DB_PATH

@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def insert_post(source: str, source_id: str, title: str = None, body: str = None,
                url: str = None, author: str = None, created_at: datetime = None,
                metadata: dict = None) -> str:
    """Insert a post, return its ID. Skips if already exists."""
    post_id = f"{source}_{source_id}"
    
    with get_connection() as conn:
        try:
            conn.execute("""
                INSERT INTO posts (id, source, source_id, title, body, url, author, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_id, source, source_id, title, body, url, author,
                created_at, json.dumps(metadata) if metadata else None
            ))
            return post_id
        except sqlite3.IntegrityError:
            # Already exists
            return None

def insert_analysis(post_id: str, fit_score: int, urgency_score: int,
                    use_case: str, reasoning: str, problem_summary: str,
                    model_used: str) -> int:
    """Insert analysis results for a post"""
    with get_connection() as conn:
        try:
            cursor = conn.execute("""
                INSERT INTO analysis (post_id, fit_score, urgency_score, use_case, 
                                      reasoning, problem_summary, model_used)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (post_id, fit_score, urgency_score, use_case, reasoning, 
                  problem_summary, model_used))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

def get_unanalyzed_posts(limit: int = 100) -> list:
    """Get posts that haven't been analyzed yet"""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT p.* FROM posts p
            LEFT JOIN analysis a ON p.id = a.post_id
            WHERE a.id IS NULL
            ORDER BY p.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]

def get_opportunities(min_fit: int = 5, min_urgency: int = 0, 
                      use_case: str = None, days: int = 7,
                      limit: int = 50) -> list:
    """Query opportunities with filters"""
    query = """
        SELECT p.*, a.fit_score, a.urgency_score, a.use_case, 
               a.reasoning, a.problem_summary, a.analyzed_at
        FROM posts p
        JOIN analysis a ON p.id = a.post_id
        WHERE a.fit_score >= ?
        AND a.urgency_score >= ?
        AND p.created_at >= datetime('now', ?)
    """
    params = [min_fit, min_urgency, f'-{days} days']
    
    if use_case:
        query += " AND a.use_case = ?"
        params.append(use_case)
    
    query += " ORDER BY a.fit_score DESC, a.urgency_score DESC LIMIT ?"
    params.append(limit)
    
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

def get_category_trends(days: int = 30) -> list:
    """Get category trends over time"""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT use_case, COUNT(*) as count,
                   AVG(fit_score) as avg_fit,
                   date(analyzed_at) as date
            FROM analysis
            WHERE analyzed_at >= datetime('now', ?)
            GROUP BY use_case, date(analyzed_at)
            ORDER BY date DESC, count DESC
        """, (f'-{days} days',)).fetchall()
        return [dict(row) for row in rows]

def get_stats() -> dict:
    """Get overall statistics"""
    with get_connection() as conn:
        stats = {}
        
        stats['total_posts'] = conn.execute(
            "SELECT COUNT(*) FROM posts"
        ).fetchone()[0]
        
        stats['analyzed_posts'] = conn.execute(
            "SELECT COUNT(*) FROM analysis"
        ).fetchone()[0]
        
        stats['high_fit_opportunities'] = conn.execute(
            "SELECT COUNT(*) FROM analysis WHERE fit_score >= 7"
        ).fetchone()[0]
        
        stats['by_source'] = dict(conn.execute(
            "SELECT source, COUNT(*) FROM posts GROUP BY source"
        ).fetchall())
        
        stats['by_use_case'] = dict(conn.execute(
            "SELECT use_case, COUNT(*) FROM analysis GROUP BY use_case ORDER BY COUNT(*) DESC"
        ).fetchall())
        
        return stats
