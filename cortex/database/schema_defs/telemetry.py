# [C5-REAL] Exergy-Maximized
"""Execution Trace Ledger and Telemetry schema."""

CREATE_LLM_TELEMETRY = """
CREATE TABLE IF NOT EXISTS llm_telemetry (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    intent          TEXT,
    resolved_by     TEXT,
    project         TEXT,
    tier            TEXT NOT NULL,
    depth           INTEGER NOT NULL,
    latency_ms      REAL,
    errors          TEXT DEFAULT '[]',
    timestamp       REAL NOT NULL,
    prompt_tokens   INTEGER,
    completion_tokens INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_LLM_TELEMETRY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_llm_telemetry_tier ON llm_telemetry(tier);
CREATE INDEX IF NOT EXISTS idx_llm_telemetry_timestamp ON llm_telemetry(timestamp);
"""

CREATE_EXECUTION_TRACE_LEDGER = """
CREATE TABLE IF NOT EXISTS execution_trace_ledger (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    origin          TEXT NOT NULL,
    cost            REAL NOT NULL,
    lineage         TEXT NOT NULL DEFAULT '[]',
    outcome         TEXT NOT NULL,
    rollback_possible BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_exec_trace_tenant ON execution_trace_ledger(tenant_id);
CREATE INDEX IF NOT EXISTS idx_exec_trace_outcome ON execution_trace_ledger(outcome);
"""

SCHEMA = [
    CREATE_LLM_TELEMETRY,
    CREATE_LLM_TELEMETRY_INDEX,
    CREATE_EXECUTION_TRACE_LEDGER,
]
