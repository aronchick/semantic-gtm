-- GTM Semantic Crawler Database Schema

-- Raw posts from all sources
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,  -- 'hn', 'reddit', 'twitter'
    source_id TEXT NOT NULL,
    title TEXT,
    body TEXT,
    url TEXT,
    author TEXT,
    created_at TIMESTAMP,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,
    UNIQUE(source, source_id)
);

-- AI analysis results
CREATE TABLE IF NOT EXISTS analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL REFERENCES posts(id),
    fit_score INTEGER CHECK(fit_score >= 0 AND fit_score <= 10),
    urgency_score INTEGER CHECK(urgency_score >= 0 AND urgency_score <= 10),
    use_case TEXT,
    reasoning TEXT,
    problem_summary TEXT,
    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_used TEXT,
    UNIQUE(post_id)
);

-- Problem taxonomy categories
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    parent_category TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    post_count INTEGER DEFAULT 0
);

-- Many-to-many: posts to categories
CREATE TABLE IF NOT EXISTS post_categories (
    post_id TEXT REFERENCES posts(id),
    category_id INTEGER REFERENCES categories(id),
    PRIMARY KEY(post_id, category_id)
);

-- Pattern tracking over time
CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    date DATE NOT NULL,
    count INTEGER DEFAULT 0,
    trend TEXT,  -- 'rising', 'falling', 'stable'
    UNIQUE(category, date)
);

-- Digest history
CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    digest_date DATE,
    content TEXT,
    opportunities_count INTEGER,
    new_patterns TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_posts_source ON posts(source);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_analysis_fit ON analysis(fit_score DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_urgency ON analysis(urgency_score DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_usecase ON analysis(use_case);
