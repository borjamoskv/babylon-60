import pytest
import sqlite3
import json
from cortex.engine.saga_orchestrator import SagaOrchestrator
from cortex.storage.wal import WAL_PATH
from cortex_rs import can_read_fact

@pytest.fixture(autouse=True)
def clean_wal():
    """Limpia la base de datos de test WAL"""
    conn = sqlite3.connect(WAL_PATH)
    conn.execute("DELETE FROM batch_wal")
    conn.commit()
    conn.close()
    yield
    conn = sqlite3.connect(WAL_PATH)
    conn.execute("DELETE FROM batch_wal")
    conn.commit()
    conn.close()

class TestSagaRollback:
    """
    Test suite para RFC-003C: Rollback and FFI boundaries
    """

    @pytest.mark.asyncio
    async def test_saga_rollback_on_zk_rejection(self):
        """
        Si ZK Guard o Rust rechazan la validación, el WAL debe marcar el evento
        como rechazado y la DB debe revertir o marcarlo rechazado.
        """
        orchestrator = SagaOrchestrator()
        fact_id, wal_event_hash = await orchestrator.generate_hypothesis(
            claim="invalid hypothesis",
            evidence={},
            agent_id="agent_1"
        )
        
        # Validar en ZK Guard forzando fallo
        sealed = await orchestrator.zk_guard.validate_and_seal(fact_id, wal_event_hash, is_valid=False)
        assert sealed is False
        
        # Verificar estado final en FactStore
        fact = await orchestrator.fact_store.get(fact_id)
        assert fact.validation_status == "rejected"
        
        # Verificar estado en WAL DB
        conn = sqlite3.connect(WAL_PATH)
        cursor = conn.execute("SELECT status FROM batch_wal WHERE event_id = ?", (fact_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "rejected"
        conn.close()
        
    @pytest.mark.asyncio
    async def test_ffi_requires_valid_wal_hash(self):
        """
        Rust rechaza el sellado si Python no provee un wal_event_hash válido,
        simulando prevención de bypass de persistencia.
        """
        orchestrator = SagaOrchestrator()
        fact_id, wal_event_hash = await orchestrator.generate_hypothesis(
            claim="valid hypothesis",
            evidence={},
            agent_id="agent_1"
        )
        
        # Pasar hash vacío
        sealed = await orchestrator.zk_guard.validate_and_seal(fact_id, "", is_valid=True)
        assert sealed is False
        
        fact = await orchestrator.fact_store.get(fact_id)
        assert fact.validation_status == "rejected"
