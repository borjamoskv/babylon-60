# [C5-REAL] Exergy-Maximized
"""Facts extensions, Full-Text Search, and Procedural Engrams schema."""

CREATE_FACTS_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    content,
    project,
    tags,
    fact_type,
    tenant_id UNINDEXED
);
"""

CREATE_FACTS_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS trg_facts_ai AFTER INSERT ON facts BEGIN
  INSERT INTO facts_fts(rowid, content, project, tags, fact_type, tenant_id)
  VALUES (new.id, new.content, new.project, new.tags, new.fact_type, new.tenant_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_facts_ad AFTER DELETE ON facts BEGIN
  DELETE FROM facts_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_facts_au AFTER UPDATE ON facts BEGIN
  DELETE FROM facts_fts WHERE rowid = old.id;
  INSERT INTO facts_fts(rowid, content, project, tags, fact_type, tenant_id)
  VALUES (new.id, new.content, new.project, new.tags, new.fact_type, new.tenant_id);
END;
"""

CREATE_PROCEDURAL_ENGRAMS = """
CREATE TABLE IF NOT EXISTS procedural_engrams (
    skill_name      TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    invocations     INTEGER NOT NULL DEFAULT 0,
    success_rate    REAL NOT NULL DEFAULT 1.0,
    avg_latency_ms  REAL NOT NULL DEFAULT 0.0,
    last_invoked    REAL NOT NULL,
    permanent       INTEGER NOT NULL DEFAULT 0
);

CREATE TRIGGER IF NOT EXISTS trg_procedural_engrams_permanent_immutability
BEFORE UPDATE OF permanent ON procedural_engrams
FOR EACH ROW
WHEN OLD.permanent = 1 AND NEW.permanent = 0
BEGIN
    SELECT RAISE(ABORT, 'Immunitas-Omega (Ω3): Unidirectional immutability violated. Cannot revert permanent=1 to permanent=0');
END;
"""

CREATE_CAUSAL_EDGES = """
CREATE TABLE IF NOT EXISTS causal_edges (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fact_hash       TEXT UNIQUE,
    fact_id         INTEGER NOT NULL,
    parent_id       INTEGER,
    signal_id       INTEGER,
    edge_type       TEXT NOT NULL DEFAULT 'triggered_by',
    confidence      REAL DEFAULT 1.0,
    agent_id        TEXT,
    project         TEXT,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (fact_id) REFERENCES facts(id)
);
"""

SCHEMA = [
    CREATE_FACTS_FTS,
    CREATE_FACTS_FTS_TRIGGERS,
    CREATE_PROCEDURAL_ENGRAMS,
    CREATE_CAUSAL_EDGES,
]
