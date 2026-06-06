import logging
import base64
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

logger = logging.getLogger("cortex.engine.causal.verification_oracle")

class InvariantViolationError(ValueError):
    """Raised when a formal system invariant is violated."""
    pass

async def verify_ledger_continuity(conn) -> bool:
    """Inv-1 & Inv-2: Re-verifies the event ledger chain cryptographic continuity."""
    try:
        from cortex.memory.ledger import EventLedgerL3
        ledger = EventLedgerL3(conn)
        res = await ledger.verify_chain("default")
        if res.get("status") == "CORRUPT":
            logger.error("[VerificationOracle] Inv-1/2 Failure: Event Ledger is corrupt! Findings: %s", res.get("findings"))
            return False
        return True
    except Exception as e:
        logger.error("[VerificationOracle] Failed to run ledger continuity check: %s", e)
        return False

async def verify_causal_dag(conn) -> bool:
    """Inv-3: Asserts the causal graph remains a Directed Acyclic Graph (no cycles)."""
    try:
        # Fetch all causal edges
        cursor = await conn.execute("SELECT fact_id, parent_id FROM causal_edges WHERE parent_id IS NOT NULL")
        edges = await cursor.fetchall()
        
        # Build adjacency list
        graph = {}
        for row in edges:
            u, v = row[0], row[1]
            if u not in graph:
                graph[u] = []
            graph[u].append(v)
            
        # Detect cycles via DFS
        visited = {}
        
        def has_cycle(node):
            visited[node] = 1 # Visiting
            for neighbor in graph.get(node, []):
                if visited.get(neighbor, 0) == 1:
                    return True
                if visited.get(neighbor, 0) == 0:
                    if has_cycle(neighbor):
                        return True
            visited[node] = 2 # Visited
            return False
            
        for node in list(graph.keys()):
            if visited.get(node, 0) == 0:
                if has_cycle(node):
                    logger.error("[VerificationOracle] Inv-3 Failure: Cycle detected in causality graph at node %s", node)
                    return False
        return True
    except Exception as e:
        logger.error("[VerificationOracle] Failed to run causal DAG check: %s", e)
        return False

async def verify_approved_auth_signatures(conn) -> bool:
    """Inv-4: Verifies all approved overrides in auth_requests have a mathematically valid Ed25519 signature."""
    try:
        cursor = await conn.execute("SELECT id, state_payload, signature, public_key FROM auth_requests WHERE status = 'APPROVED'")
        rows = await cursor.fetchall()
        
        for row in rows:
            req_id, payload, sig, pub_key_b64 = row
            if not sig or not pub_key_b64:
                logger.error("[VerificationOracle] Inv-4 Failure: Approved auth request %s is missing signature/pubkey.", req_id)
                return False
                
            # Perform Ed25519 check
            try:
                pub_bytes = base64.b64decode(pub_key_b64)
                pub_key = Ed25519PublicKey.from_public_bytes(pub_bytes)
                sig_bytes = base64.b64decode(sig)
                
                # Check signature of (state_payload) treating req_id as fact_hash
                # As done in AuthGateway: content=state_payload, fact_hash=req_id
                # Verification payload in Ed25519Signer._canonical_payload is (sha256(content):fact_hash)
                import hashlib
                content_digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                canonical_msg = f"{content_digest}:{req_id}".encode("utf-8")
                
                pub_key.verify(sig_bytes, canonical_msg)
            except Exception as e:
                logger.error("[VerificationOracle] Inv-4 Failure: Approved request %s signature verification failed: %s", req_id, e)
                return False
        return True
    except Exception as e:
        logger.error("[VerificationOracle] Failed to check auth signatures: %s", e)
        return False

async def verify_nonce_uniqueness(conn) -> bool:
    """Inv-5: Verifies that taint_nonces table has no duplicates (handled by SQLite schema but audited here)."""
    try:
        # Check if table exists
        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='taint_nonces'")
        if not await cursor.fetchone():
            return True # No nonces yet, table not created
            
        cursor = await conn.execute("SELECT nonce, COUNT(*) as c FROM taint_nonces GROUP BY nonce HAVING c > 1")
        if await cursor.fetchone():
            logger.error("[VerificationOracle] Inv-5 Failure: Duplicate nonces found in exclusion list.")
            return False
        return True
    except Exception as e:
        logger.error("[VerificationOracle] Failed to check nonces: %s", e)
        return False

async def verify_c5_state_machine(conn) -> bool:
    """Verifies all five formal invariants of the C5-REAL state machine.
    
    Returns True if all invariants are preserved.
    Raises InvariantViolationError if any invariant is violated.
    """
    logger.info("[VerificationOracle] Commencing formal C5-REAL state machine audit...")
    
    if not await verify_ledger_continuity(conn):
        raise InvariantViolationError("Inv-1/2 Violated: Event ledger continuity or cryptographic signature broken.")
        
    if not await verify_causal_dag(conn):
        raise InvariantViolationError("Inv-3 Violated: Cycle detected in causality graph.")
        
    if not await verify_approved_auth_signatures(conn):
        raise InvariantViolationError("Inv-4 Violated: Approved override is missing a valid operator signature.")
        
    if not await verify_nonce_uniqueness(conn):
        raise InvariantViolationError("Inv-5 Violated: Duplicate nonces detected in replay exclusion ledger.")
        
    logger.info("[VerificationOracle] Verification Success: All 5 invariants preserved.")
    return True
