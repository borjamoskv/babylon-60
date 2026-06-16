# [C5-REAL] Exergy-Maximized
"""Sovereign Locks (Axiom Ω₂ - Lock-Free Concurrency) schema."""

CREATE_LOCK_INTENTS = """
CREATE TABLE IF NOT EXISTS lock_intents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    resource        TEXT NOT NULL,
    agent_id        TEXT NOT NULL,
    action          TEXT NOT NULL, -- 'request', 'release'
    priority        INTEGER DEFAULT 0,
    timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT
);
"""

CREATE_LOCK_STATE = """
CREATE TABLE IF NOT EXISTS lock_state (
    resource        TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    holder_agent    TEXT,
    acquired_at     TEXT,
    expires_at      TEXT,
    queue_depth     INTEGER DEFAULT 0
);
"""

CREATE_LOCK_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_lock_intents_resource ON lock_intents(resource);
CREATE INDEX IF NOT EXISTS idx_lock_intents_agent ON lock_intents(agent_id);
"""

CREATE_LOCK_TTL_TRIGGER = """
CREATE TRIGGER IF NOT EXISTS trg_lock_ttl_release
AFTER INSERT ON lock_intents
BEGIN
    UPDATE lock_state
    SET holder_agent = NULL, acquired_at = NULL,
        expires_at = NULL, queue_depth = MAX(0, queue_depth - 1)
    WHERE expires_at IS NOT NULL AND expires_at < datetime('now');
END;
"""

SCHEMA = [
    CREATE_LOCK_INTENTS,
    CREATE_LOCK_STATE,
    CREATE_LOCK_INDEXES,
    CREATE_LOCK_TTL_TRIGGER,
]
