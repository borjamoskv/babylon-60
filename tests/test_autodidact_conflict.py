import pytest
import asyncio
import aiosqlite
import json
import os
import shutil
import uuid
from unittest.mock import patch, MagicMock, AsyncMock

from cortex.extensions.skills.autodidact.synthesis import execute_cognitive_synthesis, get_memory_manager
from cortex.memory.manager import CortexMemoryManager
from cortex.memory.working import WorkingMemoryL1
from cortex.memory.ledger import EventLedgerL3
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2
from cortex.memory.encoder import AsyncEncoder

CRYSTAL_TERMINAL_X_AUTH = {
    "status": "success",
    "data": {
        "entities": ["Terminal-X"],
        "resonancia_axiomatica": "crystalline",
        "content_markdown": "Terminal-X is an authorized sovereign gateway with cryptographic attestation and zero-trust runtime validation.",
    }
}

CRYSTAL_TERMINAL_X_ROGUE = {
    "status": "success",
    "data": {
        "entities": ["Terminal-X"],
        "resonancia_axiomatica": "crystalline",
        "content_markdown": "Terminal-X is a compromised rogue node actively exfiltrating sovereign data to hostile endpoints.",
    }
}


@pytest.mark.asyncio
async def test_autodidact_epistemic_conflict_e2e():
    """End-to-end test of Autodidact-Ω conflict detection and ledger recording (Ω9)."""
    run_id = uuid.uuid4().hex[:8]
    run_dir = os.path.abspath(f"scratch/run_{run_id}")
    db_path = os.path.join(run_dir, "conflict.db")
    l2_path = os.path.join(run_dir, "vectors.db")
    
    os.makedirs(run_dir, exist_ok=True)
            
    async with aiosqlite.connect(db_path) as conn:
        l1 = WorkingMemoryL1()
        l3 = EventLedgerL3(conn)
        await l3.ensure_table()
        
        with patch("cortex.memory.encoder.LocalEmbedder") as mock_embedder_class:
            mock_embedder = mock_embedder_class.return_value
            mock_embedder.embed.side_effect = lambda x: [0.1]*384
            mock_embedder.model_identity_hash = "test_hash"
            
            encoder = AsyncEncoder()
            l2 = SovereignVectorStoreL2(encoder=encoder, db_path=l2_path)
            # Ensure hybrid is initialized (calling _get_conn)
            l2._get_conn()
            
            assert l2._hybrid is not None, "FTS5 Hybrid Search should be active in test environment"
            
            manager = CortexMemoryManager(l1=l1, l2=l2, l3=l3, encoder=encoder)
            
            try:
                with patch("cortex.extensions.skills.autodidact.synthesis.get_memory_manager", return_value=manager), \
                     patch("cortex.extensions.skills.autodidact.synthesis.distill_sovereign_memo",
                           new=AsyncMock(return_value=CRYSTAL_TERMINAL_X_AUTH)), \
                     patch("cortex.extensions.skills.autodidact.synthesis.generate_cortex_embedding",
                           new=AsyncMock(return_value=[0.1]*384)):
                    
                    # 1. Establish a sovereign fact about 'Terminal-X'
                    res1 = await execute_cognitive_synthesis(
                        raw_data="[LOG] Terminal-X connection established",
                        source="auth_monitor"
                    )
                    assert "filtered:conflict" not in res1, f"Unexpected conflict on first store: {res1}"
                
                # 2. Inject a contradictory fact about 'Terminal-X' (same subject)
                with patch("cortex.extensions.skills.autodidact.synthesis.get_memory_manager", return_value=manager), \
                     patch("cortex.extensions.skills.autodidact.synthesis.distill_sovereign_memo",
                           new=AsyncMock(return_value=CRYSTAL_TERMINAL_X_ROGUE)), \
                     patch("cortex.extensions.skills.autodidact.synthesis.generate_cortex_embedding",
                           new=AsyncMock(return_value=[0.15]*384)):
                    
                    res2 = await execute_cognitive_synthesis(
                        raw_data="[ALERT] Terminal-X malicious behavior detected",
                        source="security_scan"
                    )
                    
                    # Ω9: Epistemic conflict must be quarantined
                    assert "filtered:conflict" in res2, f"Expected conflict, got: {res2}"
                
                # 3. Verify L3 Ledger received the conflict event
                events = await l3.get_session_events(
                    session_id="autodidact_knowledge",
                    tenant_id="sovereign"
                )
                
                conflict_events = [e for e in events if e.metadata.get("type") == "epistemic_conflict"]
                assert len(conflict_events) >= 1, f"No conflict events in L3. All events: {[e.metadata for e in events]}"
                assert conflict_events[0].metadata.get("subject_hash") is not None
                
                print("\n✅ [Ω9 VERIFIED] Epistemic Conflict recorded in Ledger.")
            finally:
                await l2.close()
    
    shutil.rmtree(run_dir, ignore_errors=True)
