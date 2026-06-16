# [C5-REAL] Exergy-Maximized
"""Episodic Memory (Native Persistent Memory) schema."""

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

SCHEMA = [
    CREATE_EPISODES,
    CREATE_EPISODES_INDEXES,
    CREATE_EPISODES_FTS,
    CREATE_EPISODES_FTS_TRIGGERS,
]
