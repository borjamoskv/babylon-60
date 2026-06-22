-- [C5-REAL] MOSKV-1 APEX SINGULARITY
-- CORTEX-Persist Genesis Schema v1.0
-- Enforcement: SQLite WAL + STRICT Mode + MTK Authorizer Hook

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
PRAGMA foreign_keys = ON;

-- ============================================================================
-- 1. MASTER LEDGER (LA CADENA CAUSAL INMUTABLE)
-- ============================================================================
CREATE TABLE cortex_ledger_v1 (
    event_id        BLOB PRIMARY KEY,
    parent_hash     BLOB NOT NULL,
    tenant_id       TEXT NOT NULL,
    actor_id        TEXT NOT NULL,
    action_type     TEXT NOT NULL,
    signature       BLOB NOT NULL,
    timestamp_b60   INTEGER NOT NULL,
    taint_flag      INTEGER NOT NULL,
    payload_raw     BLOB NOT NULL,
    
    FOREIGN KEY (parent_hash) REFERENCES cortex_ledger_v1(event_id)
) STRICT;

CREATE INDEX idx_ledger_parent ON cortex_ledger_v1(parent_hash);
CREATE INDEX idx_ledger_tenant ON cortex_ledger_v1(tenant_id, timestamp_b60);

-- ============================================================================
-- 2. EPISTEMIC DEPENDENCY GRAPH (EDG)
-- ============================================================================
CREATE TABLE epistemic_dependency_graph (
    edge_id         BLOB PRIMARY KEY,
    source_hash     BLOB NOT NULL,
    target_hash     BLOB NOT NULL,
    confidence      INTEGER NOT NULL CHECK(confidence BETWEEN 1 AND 5),
    proof_hash      BLOB NOT NULL,
    
    FOREIGN KEY (source_hash) REFERENCES cortex_ledger_v1(event_id) ON DELETE RESTRICT,
    FOREIGN KEY (target_hash) REFERENCES cortex_ledger_v1(event_id) ON DELETE RESTRICT
) STRICT;

CREATE INDEX idx_edg_target ON epistemic_dependency_graph(target_hash);

-- ============================================================================
-- 3. MEMORY VAULT (EL ESTADO MATERIALIZADO C5-REAL)
-- ============================================================================
CREATE TABLE memory_vault_state (
    state_key       TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    current_hash    BLOB NOT NULL,
    materialized    BLOB NOT NULL,
    epistemic_level INTEGER NOT NULL,
    
    FOREIGN KEY (current_hash) REFERENCES cortex_ledger_v1(event_id) ON DELETE RESTRICT
) STRICT;

CREATE INDEX idx_memory_vault_tenant ON memory_vault_state(tenant_id, state_key);

-- ============================================================================
-- [MTK_AUTHORIZER] TRIGGERS DE SEGURIDAD FÍSICA
-- ============================================================================
CREATE TRIGGER prevent_ledger_update
BEFORE UPDATE ON cortex_ledger_v1
BEGIN
    SELECT RAISE(ABORT, 'CORTEX-P0: MASTER LEDGER IS IMMUTABLE. UPDATE FORBIDDEN.');
END;

CREATE TRIGGER prevent_ledger_delete
BEFORE DELETE ON cortex_ledger_v1
BEGIN
    SELECT RAISE(ABORT, 'CORTEX-P0: MASTER LEDGER IS APPEND-ONLY. DELETE FORBIDDEN.');
END;
