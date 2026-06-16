# [C5-REAL] Exergy-Maximized
"""Consensus and Trust Graph schema."""

CREATE_AGENTS = """
CREATE TABLE IF NOT EXISTS agents (
    id              TEXT PRIMARY KEY,
    public_key      TEXT NOT NULL,
    name            TEXT NOT NULL,
    agent_type      TEXT NOT NULL DEFAULT 'ai',
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    reputation_score    REAL NOT NULL DEFAULT 0.5,
    base_reputation     REAL NOT NULL DEFAULT 0.5,
    reputation_stake    REAL NOT NULL DEFAULT 0.0,
    alignment_hits      INTEGER DEFAULT 0,
    alignment_misses    INTEGER DEFAULT 0,
    total_votes         INTEGER DEFAULT 0,
    successful_votes    INTEGER DEFAULT 0,
    disputed_votes      INTEGER DEFAULT 0,
    last_active_at      TEXT NOT NULL DEFAULT (datetime('now')),
    is_active           BOOLEAN DEFAULT TRUE,
    is_verified         BOOLEAN DEFAULT FALSE,
    meta                TEXT DEFAULT '{}'
);
"""

CREATE_VOTES_V2 = """
CREATE TABLE IF NOT EXISTS consensus_votes_v2 (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id         INTEGER NOT NULL REFERENCES facts(id),
    agent_id        TEXT NOT NULL REFERENCES agents(id),
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    vote            INTEGER NOT NULL,
    vote_weight     REAL NOT NULL,
    agent_rep_at_vote   REAL NOT NULL,
    stake_at_vote       REAL DEFAULT 0.0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    decay_factor    REAL DEFAULT 1.0,
    vote_reason     TEXT,
    meta            TEXT DEFAULT '{}',
    UNIQUE(fact_id, agent_id)
);
"""

CREATE_TRUST_EDGES = """
CREATE TABLE IF NOT EXISTS trust_edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_agent    TEXT NOT NULL REFERENCES agents(id),
    target_agent    TEXT NOT NULL REFERENCES agents(id),
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    trust_weight    REAL NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_agent, target_agent)
);
"""

CREATE_OUTCOMES = """
CREATE TABLE IF NOT EXISTS consensus_outcomes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_id         INTEGER NOT NULL REFERENCES facts(id),
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    final_state     TEXT NOT NULL,
    final_score     REAL NOT NULL,
    resolved_at     TEXT NOT NULL DEFAULT (datetime('now')),
    total_votes     INTEGER NOT NULL,
    unique_agents   INTEGER NOT NULL,
    reputation_sum  REAL NOT NULL,
    resolution_method   TEXT DEFAULT 'reputation_weighted',
    meta                TEXT DEFAULT '{}'
);
"""

CREATE_RWC_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_agents_reputation ON agents(reputation_score DESC);
CREATE INDEX IF NOT EXISTS idx_agents_active ON agents(is_active, last_active_at);
CREATE INDEX IF NOT EXISTS idx_votes_v2_fact ON consensus_votes_v2(fact_id);
CREATE INDEX IF NOT EXISTS idx_votes_v2_agent ON consensus_votes_v2(agent_id);
CREATE INDEX IF NOT EXISTS idx_trust_source ON trust_edges(source_agent);
CREATE INDEX IF NOT EXISTS idx_trust_target ON trust_edges(target_agent);
"""

SCHEMA = [
    CREATE_AGENTS,
    CREATE_VOTES_V2,
    CREATE_TRUST_EDGES,
    CREATE_OUTCOMES,
    CREATE_RWC_INDEXES,
]
