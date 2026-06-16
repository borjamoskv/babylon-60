# [C5-REAL] Exergy-Maximized
"""Signal Bus (L1 Consciousness - Cross-Tool Reactive Signaling) schema."""

CREATE_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    event_type  TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '{}',
    source      TEXT NOT NULL,
    project     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    consumed_by TEXT NOT NULL DEFAULT '[]'
);
"""

CREATE_SIGNALS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(event_type);
CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_signals_project ON signals(project);
"""

SCHEMA = [
    CREATE_SIGNALS,
    CREATE_SIGNALS_INDEXES,
]
