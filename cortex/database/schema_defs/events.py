# [C5-REAL] Exergy-Maximized
"""Entity Events (Solid-State Substrate - Append-Only Ledger) schema."""

CREATE_ENTITY_EVENTS = """
CREATE TABLE IF NOT EXISTS entity_events (
    id              TEXT PRIMARY KEY,
    entity_id       INTEGER NOT NULL,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    event_type      TEXT NOT NULL,
    payload         TEXT NOT NULL DEFAULT '{}',
    timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
    prev_hash       TEXT NOT NULL DEFAULT 'GENESIS',
    signature       TEXT NOT NULL CHECK(length(signature) > 0),
    signer          TEXT NOT NULL DEFAULT '',
    schema_version  TEXT NOT NULL DEFAULT '1'
);
"""

CREATE_ENTITY_EVENTS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ee_entity ON entity_events(entity_id);
CREATE INDEX IF NOT EXISTS idx_ee_tenant ON entity_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ee_type ON entity_events(event_type);
CREATE INDEX IF NOT EXISTS idx_ee_timestamp ON entity_events(timestamp);
"""

SCHEMA = [
    CREATE_ENTITY_EVENTS,
    CREATE_ENTITY_EVENTS_INDEXES,
]
