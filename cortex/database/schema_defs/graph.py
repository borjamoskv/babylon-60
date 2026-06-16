# [C5-REAL] Exergy-Maximized
"""Graph Memory (Knowledge Graph) schema."""

CREATE_ENTITIES = """
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT 'unknown',
    project TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    mention_count INTEGER DEFAULT 1,
    meta TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_entities_name_project ON entities(name, project);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project);
CREATE INDEX IF NOT EXISTS idx_entities_tenant ON entities(tenant_id);
"""

CREATE_ENTITY_RELATIONS = """
CREATE TABLE IF NOT EXISTS entity_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_entity_id INTEGER NOT NULL REFERENCES entities(id),
    target_entity_id INTEGER NOT NULL REFERENCES entities(id),
    tenant_id TEXT NOT NULL DEFAULT 'default',
    relation_type TEXT NOT NULL DEFAULT 'related_to',
    weight REAL DEFAULT 1.0,
    first_seen TEXT NOT NULL,
    source_fact_id INTEGER REFERENCES facts(id)
);

CREATE INDEX IF NOT EXISTS idx_relations_source ON entity_relations(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_target ON entity_relations(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_tenant ON entity_relations(tenant_id);
"""

SCHEMA = [
    CREATE_ENTITIES,
    CREATE_ENTITY_RELATIONS,
]
