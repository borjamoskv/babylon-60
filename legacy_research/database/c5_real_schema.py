# [C5-REAL] Exergy-Maximized
"""
C5-REAL Execution Kernel Schema (Gate 1).
This module defines the determinist SQLite schema implementing the Epistemic Directed Graph (EDG),
the Master Audit Ledger, and the Memory Vault. It strictly enforces the 'Babylon-60' rule,
eliminating stochastic floats and ensuring deterministic execution state.
"""

from __future__ import annotations

__all__ = [
    "CREATE_C5_AUDIT_LEDGER",
    "CREATE_C5_EDG_NODES",
    "CREATE_C5_EDG_EDGES",
    "CREATE_C5_MEMORY_VAULT",
    "C5_REAL_SCHEMA",
]

# 1. MASTER AUDIT LEDGER (La Cadena Causal)
CREATE_C5_AUDIT_LEDGER = """
CREATE TABLE IF NOT EXISTS c5_audit_ledger (
    seq_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ledger_hash     TEXT NOT NULL UNIQUE,          -- SHA-256 of payload + prev_hash
    prev_hash       TEXT NOT NULL,                 -- Immutable chain link
    agent_id        TEXT NOT NULL,                 -- SYS_ID or Ed25519 PubKey
    action_type     TEXT NOT NULL,                 -- 'EDG_MUTATION', 'MEMORY_COMMIT'
    payload_sig     TEXT NOT NULL,                 -- Ed25519 Signature
    b60_timestamp   INTEGER NOT NULL,              -- Babylon-60 Epoch (ms)
    b60_exergy_cost INTEGER NOT NULL,              -- Thermodynamic cost of mutation
    is_sealed       BOOLEAN NOT NULL DEFAULT 0,    -- 1 if processed by the MTK
    CHECK (length(ledger_hash) = 64)
);
CREATE INDEX IF NOT EXISTS idx_c5_ledger_hash ON c5_audit_ledger(ledger_hash);
"""

# 2. EPISTEMIC DIRECTED GRAPH (EDG)
CREATE_C5_EDG_NODES = """
CREATE TABLE IF NOT EXISTS c5_edg_nodes (
    node_id         TEXT PRIMARY KEY,              -- SHA-256 of structural content
    ledger_seq      INTEGER NOT NULL REFERENCES c5_audit_ledger(seq_id),
    status          TEXT NOT NULL,                 -- 'Proven', 'Inferred', 'Speculative', 'Contradicted'
    b60_confidence  INTEGER NOT NULL,              -- Range [0, 6000] (Babylon-60, 6000 = 100%)
    b60_exergy      INTEGER NOT NULL DEFAULT 0,    -- Exergetic load
    node_schema     TEXT NOT NULL,                 -- Strict definition (JSON Schema Hash)
    payload         BLOB NOT NULL,                 -- Binary state or deterministic JSON
    CHECK (status IN ('Proven', 'Inferred', 'Speculative', 'Contradicted'))
);
"""

CREATE_C5_EDG_EDGES = """
CREATE TABLE IF NOT EXISTS c5_edg_edges (
    edge_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source_node     TEXT NOT NULL REFERENCES c5_edg_nodes(node_id),
    target_node     TEXT NOT NULL REFERENCES c5_edg_nodes(node_id),
    ledger_seq      INTEGER NOT NULL REFERENCES c5_audit_ledger(seq_id),
    b60_weight      INTEGER NOT NULL,              -- Causal force [0, 6000]
    edge_type       TEXT NOT NULL,                 -- 'SUPPORTS', 'CONTRADICTS', 'DERIVES'
    UNIQUE(source_node, target_node, edge_type)
);
"""

# 3. MEMORY VAULT (Almacén de Estado Aislado)
CREATE_C5_MEMORY_VAULT = """
CREATE TABLE IF NOT EXISTS c5_memory_vault (
    vault_id        TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    node_id         TEXT NOT NULL REFERENCES c5_edg_nodes(node_id),
    ledger_seq      INTEGER NOT NULL REFERENCES c5_audit_ledger(seq_id),
    b60_timestamp   INTEGER NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT 1,
    encrypted_blob  BLOB NOT NULL,                 -- AES-GCM encrypted payload
    taint_flag      TEXT NOT NULL                  -- CORTEX-TAINT
);
CREATE INDEX IF NOT EXISTS idx_c5_vault_tenant ON c5_memory_vault(tenant_id, is_active);
"""

C5_REAL_SCHEMA = [
    CREATE_C5_AUDIT_LEDGER,
    CREATE_C5_EDG_NODES,
    CREATE_C5_EDG_EDGES,
    CREATE_C5_MEMORY_VAULT,
]
