# [C5-REAL] Exergy-Maximized
"""schema_analytics - SQLite tables for analytics, episodic memory, and telemetry in CORTEX.

Extracted from schema_extensions.py to satisfy the Landauer LOC barrier.
"""

from __future__ import annotations

# ─── Context Snapshots (Ambient Intelligence) ────────────────────────
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

# ─── Episodic Memory (Native Persistent Memory) ─────────────────────
CREATE_EPISODES = """
CREATE TABLE IF NOT EXISTS episodes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    session_id  TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    content     TEXT NOT NULL,
    project     TEXT,
    emotion     TEXT DEFAULT 'neutral',
    tags        TEXT DEFAULT '[]',
    meta        TEXT DEFAULT '{}',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_EPISODES_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_ep_tenant ON episodes(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ep_session ON episodes(session_id);
CREATE INDEX IF NOT EXISTS idx_ep_project_type ON episodes(project, event_type);
CREATE INDEX IF NOT EXISTS idx_ep_created ON episodes(created_at);
CREATE INDEX IF NOT EXISTS idx_ep_event_type ON episodes(event_type);
"""

CREATE_EPISODES_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
    content,
    event_type,
    project,
    tenant_id UNINDEXED,
    content='episodes',
    content_rowid='id'
);
"""

CREATE_EPISODES_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS trg_episodes_ai AFTER INSERT ON episodes BEGIN
  INSERT INTO episodes_fts(rowid, content, event_type, project, tenant_id)
  VALUES (new.id, new.content, new.event_type, new.project, new.tenant_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_episodes_ad AFTER DELETE ON episodes BEGIN
  INSERT INTO episodes_fts(episodes_fts, rowid, content, event_type, project, tenant_id)
  VALUES ('delete', old.id, old.content, old.event_type, old.project, old.tenant_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_episodes_au AFTER UPDATE ON episodes BEGIN
  INSERT INTO episodes_fts(episodes_fts, rowid, content, event_type, project, tenant_id)
  VALUES ('delete', old.id, old.content, old.event_type, old.project, old.tenant_id);
  INSERT INTO episodes_fts(rowid, content, event_type, project, tenant_id)
  VALUES (new.id, new.content, new.event_type, new.project, new.tenant_id);
END;
"""

# ─── Evolution State (Continuous Improvement Engine) ─────────────────
CREATE_EVOLUTION_STATE = """
CREATE TABLE IF NOT EXISTS evolution_state (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle       INTEGER NOT NULL,
    agent_domain TEXT NOT NULL,
    agent_json  TEXT NOT NULL,
    saved_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_EVOLUTION_STATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_evo_cycle ON evolution_state(cycle);
CREATE INDEX IF NOT EXISTS idx_evo_domain ON evolution_state(agent_domain);
"""

# ─── Signal Bus (L1 Consciousness - Cross-Tool Reactive Signaling) ───
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

# ─── LLM Telemetry ───────────────────────────────────────────────────
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
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_LLM_TELEMETRY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_llm_telemetry_tier ON llm_telemetry(tier);
CREATE INDEX IF NOT EXISTS idx_llm_telemetry_timestamp ON llm_telemetry(timestamp);
"""

# ─── Enrichment Queue ───────────────────────────────────────────────
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

# ─── Execution Trace Ledger ───────────────────────────────────────────
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
