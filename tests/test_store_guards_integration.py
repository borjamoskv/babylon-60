"""Integration test proving that StoreMixin.store() correctly wires to GuardPipeline."""

import pytest

from cortex.engine import CortexEngine
from cortex.extensions.interfaces.store_pipeline import StoreGuard


class RejectingGuard(StoreGuard):
    async def check(self, content, project, fact_type, meta, conn, *, tenant_id="default"):
        if "forbidden_word" in content:
            raise ValueError("Guard rejected: forbidden content")


@pytest.fixture
async def engine(tmp_path):
    """Provide a fresh CortexEngine for each test."""
    db_path = tmp_path / "test_store_guards.db"
    eng = CortexEngine(db_path=str(db_path))
    await eng.init_db()

    # Add our mocking guard
    eng._guard_pipeline.add_guard(RejectingGuard())
    yield eng


@pytest.mark.asyncio
async def test_store_wires_to_guard_pipeline(engine: CortexEngine):
    """Verify that engine.store() actually invokes the guard pipeline."""
    # Should succeed
    fact_id = await engine.store(
        project="integration",
        source="integration_test",
        fact_type="test",
        content="This is safe content",
        valid_from=None,
    )
    assert fact_id > 0

    # Should fail due to the guard
    with pytest.raises(ValueError, match="Guard rejected: forbidden content"):
        await engine.store(
            project="integration",
            source="integration_test",
            fact_type="test",
            content="This contains a forbidden_word inside",
            valid_from=None,
        )
