import struct
import time
from unittest.mock import AsyncMock

import pytest

from cortex.memory.models import CortexFactModel
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2


@pytest.fixture
def temp_db_path(tmp_path):
    return tmp_path / "test_robust_vec.db"


@pytest.fixture
def mock_encoder():
    encoder = AsyncMock()
    encoder.dimension = 384
    encoder.encode.return_value = [1] * 384
    encoder.quantize = lambda x: struct.pack(f"<{len(x)}b", *x) if isinstance(x, list) else x
    return encoder


@pytest.mark.asyncio
async def test_fallback_robust_scoring(temp_db_path, mock_encoder):
    """
    Exhaustive integration test for the fallback scoring mechanics
    in SovereignVectorStoreL2. Tests that cortex_decay, success_rate, and exergy_score
    are properly incorporated into final_score during fallback.
    """
    store = SovereignVectorStoreL2(encoder=mock_encoder, db_path=temp_db_path, half_life_days=7)

    # We simulate being in fallback mode by forcing _vector_enabled = False for BOTH
    # memorize and recall, simulating an environment without sqlite-vec where tables don't exist
    embedding_vec = [1] * 384
    now = time.time()

    # Fact 1: Old fact, low exergy (0.0), low success rate -> should be lowest
    fact1 = CortexFactModel(
        id="fact_decayed",
        tenant_id="test_tenant",
        project_id="test_proj",
        content="como modelo de lenguaje",
        embedding=embedding_vec,
        timestamp=now - (14 * 24 * 3600),  # 14 days old (2 half-lives)
        is_diamond=False,
        is_bridge=False,
        confidence="high",
        success_rate=0.5,
        cognitive_layer="semantic",
        parent_decision_id=None,
        metadata={},
    )

    # Fact 2: Old but diamond fact -> should NOT decay (decay=1.0)
    fact2 = CortexFactModel(
        id="fact_diamond",
        tenant_id="test_tenant",
        project_id="test_proj",
        content="very important core axiom",
        embedding=embedding_vec,
        timestamp=now - (14 * 24 * 3600),  # 14 days old
        is_diamond=True,
        is_bridge=False,
        confidence="high",
        success_rate=0.8,
        cognitive_layer="semantic",
        parent_decision_id=None,
        metadata={},
    )

    # Fact 3: Very fresh fact, normal exergy, perfect success rate
    fact3 = CortexFactModel(
        id="fact_fresh_exergy",
        tenant_id="test_tenant",
        project_id="test_proj",
        content="cortex vector zero-trust multi-tenant semantic search algorithm implementation",  # Normal exergy (1.0)
        embedding=embedding_vec,
        timestamp=now,  # fresh, decay = 1.0
        is_diamond=False,
        is_bridge=False,
        confidence="high",
        success_rate=1.0,
        cognitive_layer="semantic",
        parent_decision_id=None,
        metadata={},
    )

    # Insert
    for f in [fact1, fact2, fact3]:
        store._vector_enabled = False
        await store.memorize(f)

    # Recall
    results = await store.recall_secure(
        tenant_id="test_tenant",
        project_id="test_proj",
        query="cortex logic",
        limit=5,
    )

    assert len(results) == 3

    # Ranking logic expectations:
    # fact3: fresh (decay=1.0) * success(1.0) * exergy (1.0) = 1.0
    # fact2: diamond (decay=1.0) * success(0.8) * exergy (1.0) = 0.8
    # fact1: old (decay=0.25) * success(0.5) * exergy (0.0) = 0.0

    results.sort(key=lambda x: getattr(x, "_recall_score", 0), reverse=True)

    assert results[0].id == "fact_fresh_exergy"
    assert results[1].id == "fact_diamond"
    assert results[2].id == "fact_decayed"

    assert getattr(results[0], "_recall_score", 0) > getattr(results[1], "_recall_score", 0)
    assert getattr(results[1], "_recall_score", 0) > getattr(results[2], "_recall_score", 0)

    await store.close()
