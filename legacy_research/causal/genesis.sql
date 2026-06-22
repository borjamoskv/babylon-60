-- C5-REAL: S_0 GENESIS BLOCK DDL
-- Enforces BABYLON-60 Epistemology, WAL mode, and strict typings.

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;

-- Nivel 0: The Epistemic Nodes (Vertices)
CREATE TABLE IF NOT EXISTS epistemic_nodes (
    node_id TEXT PRIMARY KEY, -- SHA-256 Hash of payload + salt
    tenant_id TEXT NOT NULL,
    genesis_timestamp INTEGER NOT NULL, -- BABYLON-60 scaled integer
    ontology_type TEXT NOT NULL CHECK(ontology_type IN ('AXIOM', 'OBSERVATION', 'INTENT', 'LEDGER_SEAL')),
    payload JSON NOT NULL,
    cryptographic_taint TEXT NOT NULL,
    is_invalidated INTEGER NOT NULL DEFAULT 0, -- 0 or 1
    confidence_level INTEGER NOT NULL CHECK(confidence_level BETWEEN 0 AND 5)
) STRICT;

-- Nivel 0: The Causal Edges (Transitions)
CREATE TABLE IF NOT EXISTS causal_edges (
    edge_id TEXT PRIMARY KEY,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    transition_type TEXT NOT NULL CHECK(transition_type IN ('DERIVES', 'INVALIDATES', 'ACTUATES', 'VERIFIES')),
    transition_hash TEXT NOT NULL,
    FOREIGN KEY(source_node_id) REFERENCES epistemic_nodes(node_id),
    FOREIGN KEY(target_node_id) REFERENCES epistemic_nodes(node_id)
) STRICT;

-- Nivel 0: Kinetic Actuator Queue
CREATE TABLE IF NOT EXISTS intent_queue (
    intent_id TEXT PRIMARY KEY,
    epistemic_node_id TEXT NOT NULL UNIQUE,
    actuator_target TEXT NOT NULL,
    execution_payload JSON NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PENDING', 'EXECUTING', 'COMMITTED', 'FAILED')),
    lock_version INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(epistemic_node_id) REFERENCES epistemic_nodes(node_id)
) STRICT;
