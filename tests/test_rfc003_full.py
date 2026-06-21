import pytest
import json
import time
from cortex.reality.rul import RealityClaim, Source, submit_claim
from cortex.engine.saga_orchestrator import SagaOrchestrator
from cortex_rs import validate_exergy_mutation, can_read_fact

class TestFullStackHardening:
    """
    Prueba end-to-end: RUL → EDG → BFT → WAL → Staging
    """
    
    @pytest.mark.asyncio
    async def test_complete_hypothesis_lifecycle(self):
        # 1. RUL: Registrar claim externo sobre Gemini
        claim = RealityClaim(
            statement="Gemini 1.5 Pro context window is 1M tokens",
            domain="llm",
            sources=[Source(
                url="https://ai.google.dev/gemini-api/docs/models",
                fetch_hash="sha256:abc123",
                fetched_at_epoch_ms=int(time.time()*1000)
            )]
        )
        status = submit_claim(claim)
        assert status == "verified"
        
        # 2. Saga: Generar hipótesis basada en claim verificado
        orchestrator = SagaOrchestrator()
        fact_id, wal_event_hash = await orchestrator.generate_hypothesis(
            claim="latency improves with cache warmup",
            evidence={"source_claim_id": claim.claim_id},
            agent_id="agent_1"
        )
        
        # 3. Verificar que está en staging (no legible)
        fact = await orchestrator.fact_store.get(fact_id)
        assert fact.epistemic_status == "staging"
        
        # 4. ZK-Guard valida y sella, requiriendo el hash del WAL
        sealed = await orchestrator.zk_guard.validate_and_seal(fact_id, wal_event_hash, is_valid=True)
        assert sealed is True
        
        # 5. Ahora está sealed y disponible
        fact = await orchestrator.fact_store.get(fact_id)
        assert fact.epistemic_status == "sealed"
        assert can_read_fact(fact.fact_json, "any_agent") is True
        
        # 6. EDG puede consumir
        await orchestrator.edg.inject_node(fact_id)
        node = await orchestrator.edg.get_node(fact_id)
        assert node is not None
        
    def test_exergy_mutation_requires_rul_claim(self):
        """
        No se puede mutar exergía sin claim RUL verificado.
        """
        mutation = {
            "node_id": "exergy_node",
            "delta": 1.5,
            "reason": "high_extraction",
            "epoch_ms": 1717027200000,
            "signatures": ["sig1", "sig2", "sig3"],  # 3/9 → insuficiente
            "zk_proof": "proof_abc",
        }
        
        with pytest.raises(ValueError, match="MissingRULClaim"):
            validate_exergy_mutation(json.dumps(mutation), ["exergy_node"])
