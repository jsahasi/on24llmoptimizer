PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS benchmark_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date        TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    status          TEXT NOT NULL DEFAULT 'running',
    total_queries   INTEGER NOT NULL DEFAULT 0,
    completed_queries INTEGER NOT NULL DEFAULT 0,
    error_message   TEXT,
    trigger_type    TEXT NOT NULL DEFAULT 'manual'
);

CREATE INDEX IF NOT EXISTS idx_runs_date ON benchmark_runs(run_date);
CREATE INDEX IF NOT EXISTS idx_runs_status ON benchmark_runs(status);

CREATE TABLE IF NOT EXISTS queries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    query_text      TEXT NOT NULL UNIQUE,
    category        TEXT NOT NULL,
    subcategory     TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_queries_category ON queries(category);

CREATE TABLE IF NOT EXISTS responses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL REFERENCES benchmark_runs(id),
    query_id        INTEGER NOT NULL REFERENCES queries(id),
    llm_engine      TEXT NOT NULL,
    model_name      TEXT NOT NULL,
    raw_response    TEXT NOT NULL,
    response_metadata TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_responses_run ON responses(run_id);
CREATE INDEX IF NOT EXISTS idx_responses_query ON responses(query_id);
CREATE INDEX IF NOT EXISTS idx_responses_engine ON responses(llm_engine);

CREATE TABLE IF NOT EXISTS mentions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id     INTEGER NOT NULL REFERENCES responses(id),
    run_id          INTEGER NOT NULL REFERENCES benchmark_runs(id),
    query_id        INTEGER NOT NULL REFERENCES queries(id),
    brand           TEXT NOT NULL,
    mention_position INTEGER NOT NULL,
    mention_context TEXT NOT NULL,
    sentiment       TEXT NOT NULL,
    sentiment_score REAL,
    is_primary_recommendation INTEGER DEFAULT 0,
    llm_engine      TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mentions_brand ON mentions(brand);
CREATE INDEX IF NOT EXISTS idx_mentions_run ON mentions(run_id);
CREATE INDEX IF NOT EXISTS idx_mentions_query ON mentions(query_id);

CREATE TABLE IF NOT EXISTS citations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    response_id     INTEGER NOT NULL REFERENCES responses(id),
    run_id          INTEGER NOT NULL REFERENCES benchmark_runs(id),
    query_id        INTEGER NOT NULL REFERENCES queries(id),
    url             TEXT NOT NULL,
    url_domain      TEXT NOT NULL,
    title           TEXT,
    brand_association TEXT,
    is_on24_www     INTEGER DEFAULT 0,
    is_on24_event   INTEGER DEFAULT 0,
    llm_engine      TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_citations_domain ON citations(url_domain);
CREATE INDEX IF NOT EXISTS idx_citations_brand ON citations(brand_association);
CREATE INDEX IF NOT EXISTS idx_citations_run ON citations(run_id);

CREATE TABLE IF NOT EXISTS daily_metrics (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date            TEXT NOT NULL,
    run_id              INTEGER NOT NULL REFERENCES benchmark_runs(id),
    query_id            INTEGER NOT NULL REFERENCES queries(id),
    query_category      TEXT NOT NULL,
    llm_engine          TEXT NOT NULL,
    brand               TEXT NOT NULL,
    is_mentioned        INTEGER NOT NULL DEFAULT 0,
    mention_count       INTEGER NOT NULL DEFAULT 0,
    first_mention_position INTEGER,
    is_primary_recommendation INTEGER DEFAULT 0,
    avg_sentiment_score REAL,
    dominant_sentiment  TEXT,
    citation_count      INTEGER DEFAULT 0,
    www_citation_count  INTEGER DEFAULT 0,
    event_citation_count INTEGER DEFAULT 0,
    is_winner           INTEGER DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(run_id, query_id, llm_engine, brand)
);

CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_metrics(run_date);
CREATE INDEX IF NOT EXISTS idx_daily_brand ON daily_metrics(brand);
CREATE INDEX IF NOT EXISTS idx_daily_category ON daily_metrics(query_category);
CREATE INDEX IF NOT EXISTS idx_daily_engine ON daily_metrics(llm_engine);
