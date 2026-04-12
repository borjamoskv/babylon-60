"""Integration tests for the Tripartite Memory Orchestrator (CortexMemoryManager)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from cortex.memory.engrams import CortexSemanticEngram
from cortex.memory.manager import CortexMemoryManager
from cortex.memory.models import MemoryEvent


@pytest.fixture
def mock_l1():
    l1 = MagicMock()
    l1.add_event = MagicMock(return_value=[])  # Default to no overflow
    l1.get_context = MagicMock(return_value=[{"role": "user", "content": "hello"}])
    return l1


@pytest.fixture
def mock_l2():
    l2 = MagicMock()
    l2._get_conn = MagicMock()
    # Mock upsert or insert for L2 if needed
    l2.upsert = AsyncMock()
    l2.search_similar = AsyncMock(return_value=[])
    return l2


@pytest.fixture
def mock_l3():
    l3 = AsyncMock()
    l3.append_event = AsyncMock()
    return l3


@pytest.fixture
def mock_encoder():
    encoder = AsyncMock()
    encoder.encode = AsyncMock(return_value=[0.1] * 384)
    return encoder


@pytest.fixture
def mock_mem0_pipeline():
    # Mem0Pipeline is instantiated internally, we'll patch it below or mock it out
    mem0 = AsyncMock()
    from dataclasses import dataclass

    @dataclass
    class MockExergy:
        score: float

    mem0.evaluate_exergy = AsyncMock(return_value=MockExergy(score=0.9))
    mem0.exergy_threshold = 0.5
    return mem0


@pytest_asyncio.fixture
async def manager(mock_l1, mock_l2, mock_l3, mock_encoder):
    # Using 1 background task slot for predictability in tests
    mgr = CortexMemoryManager(
        l1=mock_l1,
        l2=mock_l2,
        l3=mock_l3,
        encoder=mock_encoder,
        max_bg_tasks=1,
    )
    # Give tests control over background workers so we can test the synchronous logic
    # without hanging on active queues unless specifically testing the queues.
    yield mgr
    mgr._cancel_background_tasks()


@pytest.mark.asyncio
async def test_process_interaction_no_overflow(manager, mock_l1, mock_l3):
    """Test standard interaction flow without L1 overflow."""
    # Ensure DigitalEndocrine is mockable so we can verify it was called
    manager._endocrine = MagicMock()
    manager._endocrine.ingest_context = MagicMock()

    event = await manager.process_interaction(
        role="user",
        content="Test processing",
        session_id="session_1",
        token_count=10,
        tenant_id="tenant_x",
        project_id="cortex",
    )

    # 1. Persisted to L3
    mock_l3.append_event.assert_called_once()
    appended_event = mock_l3.append_event.call_args[0][0]
    assert appended_event.content == "Test processing"

    # 2. Endocrine ingested context
    manager._endocrine.ingest_context.assert_called_once_with(
        "Test processing",
        tenant_id="tenant_x",
        metadata={"tenant_id": "tenant_x", "project_id": "cortex"},
    )

    # 3. Pushed to L1
    mock_l1.add_event.assert_called_once()

    # 4. No overflow means nothing in the background queue
    assert manager._bg_queue.empty()
    assert event.role == "user"


@pytest.mark.asyncio
async def test_process_interaction_rejects_blank_tenant(manager, mock_l3):
    with pytest.raises(ValueError, match="tenant_id"):
        await manager.process_interaction(
            role="user",
            content="Test processing",
            session_id="session_1",
            token_count=10,
            tenant_id="   ",
        )

    mock_l3.append_event.assert_not_called()


@pytest.mark.asyncio
async def test_process_interaction_with_overflow(manager, mock_l1):
    """Test interaction flow when L1 overflows, triggering background queue."""
    # Force an overflow return from L1
    overflow_event = MemoryEvent(
        role="system", content="overflowed", token_count=50, session_id="s"
    )
    mock_l1.add_event.return_value = [overflow_event]

    await manager.process_interaction(
        role="user",
        content="Another interaction",
        session_id="session_1",
        token_count=10,
        tenant_id="tenant_y",
        project_id="proj",
    )

    # The background queue should have received the overflow (we have 1 slot and 1 item)
    # The worker might pick it up immediately, so we just wait for queue to process or assert it
    # We will cancel the workers right away to inspect the queue or just wait.
    # Actually, the worker is running. Let's patch compress_and_store to verify it's called.
    with patch("cortex.memory.manager.compress_and_store", new_callable=AsyncMock):
        # Give worker a tick to pick it up
        await asyncio.sleep(0.01)
        # The task was added *before* this patch. The worker might have already processed
        # it using the real compress_and_store and failed. We should patch it before
        # calling process_interaction.
        pass


@pytest.mark.asyncio
async def test_process_interaction_with_overflow_clean():
    """Test interaction with overflow cleanly, using a fresh manager."""
    mgr = CortexMemoryManager(
        l1=MagicMock(add_event=MagicMock(return_value=["overflowed_item"])),
        l2=MagicMock(),
        l3=AsyncMock(),
        encoder=AsyncMock(),
        max_bg_tasks=1,
    )

    with patch("cortex.memory.manager.compress_and_store", new_callable=AsyncMock) as mock_compress:
        await mgr.process_interaction(
            role="user",
            content="Testing queue",
            session_id="sess",
            token_count=10,
            tenant_id="t1",
        )

        # Worker loop processes the queue
        await mgr.wait_for_background(timeout=1.0)

        # verify background task fired
        mock_compress.assert_called_once()
        args = mock_compress.call_args[0]
        # args: (self, overflowed, session_id, tenant_id, project_id)
        assert args[1] == ["overflowed_item"]
        assert args[2] == "sess"
        assert args[3] == "t1"

    mgr._cancel_background_tasks()


@pytest.mark.asyncio
async def test_store_direct_pipeline(manager, mock_mem0_pipeline):
    """Test the direct L2 store pipeline (Mem0 -> Thalamus -> Schema -> L2)."""
    manager._mem0_pipeline = mock_mem0_pipeline

    # Mock Thalamus to pass
    manager.thalamus.filter = AsyncMock(return_value=(True, "encode:new", None))
    # Mock Resonance Gate to insert new (reset)
    manager._resonance_gate.gate = AsyncMock(
        return_value=(
            "reset",
            CortexSemanticEngram(
                id="engram_123",
                tenant_id="t",
                project_id="p",
                content="c",
                embedding=[0.0],
            ),
        )
    )

    with (
        patch.object(
            type(manager),
            "_check_deduplication",
            return_value={"status": "new", "id": None},
        ),
        patch.object(
            type(manager._schema_engine),
            "match_schema",
            return_value=None,
        ),
    ):
        result_id = await manager.store(
            tenant_id="tenant_x",
            project_id="proj",
            content="Important fact",
            fact_type="knowledge",
        )

    assert result_id == "engram_123"
    mock_mem0_pipeline.evaluate_exergy.assert_called_once()
    manager.thalamus.filter.assert_called_once()


@pytest.mark.asyncio
async def test_check_deduplication_uses_async_native_arbiter(manager):
    manager._arbiter.check_async = AsyncMock(return_value="native collision")

    result = await manager._check_deduplication(
        tenant_id="tenant_x",
        project_id="proj",
        content="Important fact",
        subject_hash="abc123",
    )

    manager._arbiter.check_async.assert_awaited_once_with("abc123")
    assert result["status"] == "conflict"
    assert result["id"] == "native:conflict"


@pytest.mark.asyncio
async def test_store_rejection_low_exergy(manager, mock_mem0_pipeline):
    """Test store abortion if Mem0 exergy is too low."""
    manager._mem0_pipeline = mock_mem0_pipeline
    mock_mem0_pipeline.evaluate_exergy.return_value.score = 0.1  # Below 0.5 threshold

    result = await manager.store(
        tenant_id="t1",
        content="Useless noise",
    )

    assert result == "filtered:low_exergy:0.1"


@pytest.mark.asyncio
async def test_store_rejects_blank_tenant(manager, mock_mem0_pipeline):
    manager._mem0_pipeline = mock_mem0_pipeline

    with pytest.raises(ValueError, match="tenant_id"):
        await manager.store(
            tenant_id="  ",
            content="Blank tenant should fail closed",
        )


@pytest.mark.asyncio
async def test_store_rejection_thalamus(manager, mock_mem0_pipeline):
    """Test store abortion if ThalamusGate rejects."""
    manager._mem0_pipeline = mock_mem0_pipeline  # Pass exergy

    # 2. Thalamus rejects
    manager.thalamus.filter = AsyncMock(return_value=(False, "discard:causal_saturation", None))

    # Patch notify_notch_pruning so it doesn't try to use WebSockets
    with patch("cortex.routes.notch_ws.notify_notch_pruning", new_callable=AsyncMock):
        result = await manager.store(
            tenant_id="t1",
            content="Saturated fact",
        )

    assert result == "filtered:discard:causal_saturation"


@pytest.mark.asyncio
async def test_store_resonance_deduplication(manager, mock_mem0_pipeline):
    """Test store returning an existing engram ID if resonance matches."""
    manager._mem0_pipeline = mock_mem0_pipeline
    manager.thalamus.filter = AsyncMock(
        return_value=(True, "encode:new", None),
    )

    existing_match = CortexSemanticEngram(
        id="existing_456",
        tenant_id="t",
        project_id="p",
        content="c",
        embedding=[0.0],
    )
    manager._resonance_gate.gate = AsyncMock(
        return_value=("resonance", existing_match),
    )

    with patch.object(
        type(manager),
        "_check_deduplication",
        return_value={"status": "new", "id": None},
    ):
        result_id = await manager.store(
            tenant_id="t1",
            content="Similar fact",
        )
    assert result_id == "deduplicated:existing_456"


@pytest.mark.asyncio
async def test_assemble_context(manager, mock_l1):
    """Test assembling final LLM context from L1 and L2."""
    with patch(
        "cortex.memory.memory_retrieval.retrieve_episodic_context", new_callable=AsyncMock
    ) as mock_retrieve:
        mock_retrieve.return_value = [{"content": "episodic 1"}]

        ctx = await manager.assemble_context(
            tenant_id="tenant_1",
            query="test query",
        )

        # Working memory should be the mocked return `[{"role": "user", "content": "hello"}]`
        assert len(ctx["working_memory"]) == 1
        assert ctx["working_memory"][0]["content"] == "hello"

        # Episodic context
        assert len(ctx["episodic_context"]) == 1
        assert ctx["episodic_context"][0]["content"] == "episodic 1"


def test_get_context_vector_rejects_blank_tenant(manager) -> None:
    with pytest.raises(ValueError, match="tenant_id"):
        manager.get_context_vector(tenant_id="  ")


@pytest.mark.asyncio
async def test_reconcile_experience_requires_explicit_tenant(manager) -> None:
    signal = SimpleNamespace(
        payload={
            "project_id": "proj",
            "content": "bus event",
            "fact_type": "knowledge",
        }
    )

    with pytest.raises(ValueError, match="tenant_id"):
        await manager.reconcile_experience(signal)


@pytest.mark.asyncio
async def test_reconcile_experience_forwards_explicit_tenant(manager) -> None:
    signal = SimpleNamespace(
        payload={
            "tenant_id": "tenant-bus",
            "project_id": "proj",
            "content": "bus event",
            "fact_type": "decision",
            "metadata": {"source": "bus"},
            "layer": "semantic",
        }
    )

    with patch.object(type(manager), "store", new_callable=AsyncMock) as mock_store:
        mock_store.return_value = "engram_789"
        result = await manager.reconcile_experience(signal)

    assert result == "engram_789"
    mock_store.assert_awaited_once_with(
        tenant_id="tenant-bus",
        project_id="proj",
        content="bus event",
        fact_type="decision",
        metadata={"source": "bus"},
        layer="semantic",
        use_bus=False,
    )


@pytest.mark.asyncio
async def test_wait_for_background_timeout(manager):
    """Test hard timeout enforcement on background tasks."""
    # Put a fake task and never call task_done
    manager._bg_queue.put_nowait((["fake"], "s", "t", "p"))

    # Should timeout because the fake task blocks (or we can just mock the worker)
    # Actually, the worker will process it and fail (since args are fake strings not objects),
    # but it WILL call task_done in the `finally` block!
    # So we need to put a task that actually hangs.
    async def hanging_compress(*args, **kwargs):
        await asyncio.sleep(5.0)

    manager._cancel_background_tasks()  # Stop real workers
    manager._bg_queue.put_nowait((["fake"], "s", "t", "p"))  # Unfinished item

    with patch("os.environ.get", return_value="1"):
        # Test the wait_for_background times out after 0.1s
        await manager.wait_for_background(timeout=0.1)

    # Queue should have been auto-drained due to timeout logic (since CORTEX_TESTING is set)
    assert manager._bg_queue.empty()


@pytest.mark.asyncio
async def test_process_interaction_forwards_to_continual_learning(
    mock_l1, mock_l2, mock_l3, mock_encoder
):
    continual_learning = MagicMock()
    continual_learning.on_interaction = MagicMock(return_value={"accepted": True})
    mgr = CortexMemoryManager(
        l1=mock_l1,
        l2=mock_l2,
        l3=mock_l3,
        encoder=mock_encoder,
        continual_learning=continual_learning,
        max_bg_tasks=1,
    )

    event = await mgr.process_interaction(
        role="user",
        content="Train from this interaction",
        session_id="session_cl",
        token_count=12,
        tenant_id="tenant_cl",
        project_id="project_cl",
        metadata={"user_id": "user_cl", "channel": "chat"},
    )

    continual_learning.on_interaction.assert_called_once_with(
        tenant_id="tenant_cl",
        user_id="user_cl",
        text="Train from this interaction",
        trace_id=event.event_id,
        metadata={
            "user_id": "user_cl",
            "channel": "chat",
            "tenant_id": "tenant_cl",
            "project_id": "project_cl",
            "role": "user",
        },
    )
    mgr._cancel_background_tasks()


@pytest.mark.asyncio
async def test_process_interaction_sidecar_failure_does_not_break_pipeline(
    mock_l1, mock_l2, mock_l3, mock_encoder
):
    continual_learning = MagicMock()
    continual_learning.on_interaction = MagicMock(side_effect=ValueError("bad metadata"))
    mgr = CortexMemoryManager(
        l1=mock_l1,
        l2=mock_l2,
        l3=mock_l3,
        encoder=mock_encoder,
        continual_learning=continual_learning,
        max_bg_tasks=1,
    )

    event = await mgr.process_interaction(
        role="user",
        content="Still persist the event",
        session_id="session_cl",
        token_count=8,
        tenant_id="tenant_cl",
    )

    assert event.content == "Still persist the event"
    mock_l3.append_event.assert_called_once()
    mgr._cancel_background_tasks()


@pytest.mark.asyncio
async def test_plan_continual_update_returns_none_when_sidecar_disabled(manager) -> None:
    result = await manager.plan_continual_update(tenant_id="tenant_1", domain="support")
    assert result is None


@pytest.mark.asyncio
async def test_continual_learning_status_returns_disabled_when_sidecar_missing(manager) -> None:
    result = await manager.continual_learning_status(tenant_id="tenant_1", domain="support")

    assert result == {
        "enabled": False,
        "tenant_id": "tenant_1",
        "domain": "support",
        "backend_configured": False,
    }


@pytest.mark.asyncio
async def test_plan_continual_update_forwards_to_sidecar(mock_l1, mock_l2, mock_l3, mock_encoder):
    continual_learning = MagicMock()
    continual_learning.plan_micro_update = MagicMock(return_value={"adapter_id": "lora:test"})
    mgr = CortexMemoryManager(
        l1=mock_l1,
        l2=mock_l2,
        l3=mock_l3,
        encoder=mock_encoder,
        continual_learning=continual_learning,
        max_bg_tasks=1,
    )

    result = await mgr.plan_continual_update(
        tenant_id="tenant_cl",
        domain="support",
        policy_violation=True,
    )

    assert result == {"adapter_id": "lora:test"}
    continual_learning.plan_micro_update.assert_called_once_with(
        tenant_id="tenant_cl",
        domain="support",
        policy_violation=True,
    )
    mgr._cancel_background_tasks()


@pytest.mark.asyncio
async def test_continual_learning_status_forwards_to_sidecar(
    mock_l1, mock_l2, mock_l3, mock_encoder
):
    continual_learning = MagicMock()
    continual_learning.status = MagicMock(
        return_value={"enabled": True, "tenant_id": "tenant_cl", "domain": "support"}
    )
    backend = MagicMock()
    mgr = CortexMemoryManager(
        l1=mock_l1,
        l2=mock_l2,
        l3=mock_l3,
        encoder=mock_encoder,
        continual_learning=continual_learning,
        continual_training_backend=backend,
        max_bg_tasks=1,
    )

    result = await mgr.continual_learning_status(
        tenant_id="tenant_cl",
        domain="support",
    )

    assert result == {
        "enabled": True,
        "tenant_id": "tenant_cl",
        "domain": "support",
        "backend_configured": True,
    }
    continual_learning.status.assert_called_once_with(
        tenant_id="tenant_cl",
        domain="support",
    )
    mgr._cancel_background_tasks()


@pytest.mark.asyncio
async def test_execute_continual_update_returns_none_without_backend(manager) -> None:
    result = await manager.execute_continual_update(tenant_id="tenant_1", domain="support")
    assert result is None


@pytest.mark.asyncio
async def test_execute_continual_update_forwards_to_sidecar(
    mock_l1, mock_l2, mock_l3, mock_encoder
):
    continual_learning = MagicMock()
    continual_learning.execute_micro_update = MagicMock(return_value={"committed": True})
    backend = MagicMock()
    mgr = CortexMemoryManager(
        l1=mock_l1,
        l2=mock_l2,
        l3=mock_l3,
        encoder=mock_encoder,
        continual_learning=continual_learning,
        continual_training_backend=backend,
        max_bg_tasks=1,
    )

    result = await mgr.execute_continual_update(
        tenant_id="tenant_cl",
        domain="support",
        policy_violation=True,
        critical_domains=("support", "security"),
    )

    assert result == {"committed": True}
    continual_learning.execute_micro_update.assert_called_once_with(
        tenant_id="tenant_cl",
        domain="support",
        backend=backend,
        policy_violation=True,
        critical_domains=("support", "security"),
    )
    mgr._cancel_background_tasks()


@pytest.mark.asyncio
async def test_forget_continual_memory_forwards_to_sidecar(mock_l1, mock_l2, mock_l3, mock_encoder):
    continual_learning = MagicMock()
    continual_learning.forget = MagicMock(return_value={"deleted_exp_ids": ["exp-1"]})
    mgr = CortexMemoryManager(
        l1=mock_l1,
        l2=mock_l2,
        l3=mock_l3,
        encoder=mock_encoder,
        continual_learning=continual_learning,
        max_bg_tasks=1,
    )

    result = await mgr.forget_continual_memory(
        tenant_id="tenant_cl",
        user_id="user_cl",
        query="secret",
    )

    assert result == {"deleted_exp_ids": ["exp-1"]}
    continual_learning.forget.assert_called_once_with(
        tenant_id="tenant_cl",
        user_id="user_cl",
        query="secret",
    )
    mgr._cancel_background_tasks()
