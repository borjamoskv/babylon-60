# [C5-REAL] Exergy-Maximized
"""Context Snapshots (Ambient Intelligence) schema."""

CREATE_CONTEXT_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS context_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    active_project  TEXT,
    confidence      TEXT NOT NULL,
    signals_used    INTEGER NOT NULL,
    summary         TEXT NOT NULL,
    signals_json    TEXT,
    projects_json   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_CONTEXT_SNAPSHOTS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_ctx_snap_project ON context_snapshots(active_project);
CREATE INDEX IF NOT EXISTS idx_ctx_snap_created ON context_snapshots(created_at);
"""

SCHEMA = [
    CREATE_CONTEXT_SNAPSHOTS,
    CREATE_CONTEXT_SNAPSHOTS_INDEX,
]
