# [C5-REAL] Exergy-Maximized
"""Enrichment Queue (P0 Decoupling) schema."""

CREATE_ENRICHMENT_JOBS = """
CREATE TABLE IF NOT EXISTS enrichment_jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          TEXT UNIQUE,
    event_id        TEXT,
    fact_id         INTEGER NOT NULL REFERENCES facts(id),
    job_type        TEXT NOT NULL DEFAULT 'embedding',
    status          TEXT NOT NULL DEFAULT 'queued',
    priority        INTEGER DEFAULT 0,
    attempts        INTEGER DEFAULT 0,
    last_error      TEXT,
    next_attempt_ts TEXT,
    next_attempt_at TEXT,
    payload         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(event_id) REFERENCES entity_events(id) ON DELETE CASCADE
);
"""

CREATE_ENRICHMENT_JOBS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_enrichment_jobs_status ON enrichment_jobs(status, priority DESC);
CREATE INDEX IF NOT EXISTS idx_enrichment_jobs_fact ON enrichment_jobs(fact_id);
"""

SCHEMA = [
    CREATE_ENRICHMENT_JOBS,
    CREATE_ENRICHMENT_JOBS_INDEXES,
]
