from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from cortex.memory.semantic_ram import DynamicSemanticSpace


@pytest.mark.asyncio
async def test_store_with_heartbeat_preserves_tenant_in_buffer() -> None:
    space = DynamicSemanticSpace(store=MagicMock(), manager=SimpleNamespace(store=AsyncMock()))

    await space.store_with_heartbeat(
        project="proj-a",
        content="heartbeat fact",
        fact_type="knowledge",
        tenant_id="tenant-a",
    )

    buffered = space.autonomic_buffer.flush()

    assert len(buffered) == 1
    assert buffered[0]["tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_force_autonomic_flush_persists_each_fact_under_its_original_tenant() -> None:
    manager = SimpleNamespace(store=AsyncMock())
    space = DynamicSemanticSpace(store=MagicMock(), manager=manager)

    space.autonomic_buffer.add(
        {
            "tenant_id": "tenant-a",
            "project": "proj-a",
            "content": "fact a",
            "fact_type": "knowledge",
            "timestamp": "1",
        }
    )
    space.autonomic_buffer.add(
        {
            "tenant_id": "tenant-b",
            "project": "proj-b",
            "content": "fact b",
            "fact_type": "decision",
            "timestamp": "2",
        }
    )

    await space.force_autonomic_flush(reason="test")
    if space._active_flushes:
        await asyncio.gather(*tuple(space._active_flushes))

    assert manager.store.await_args_list == [
        call(
            tenant_id="tenant-a",
            project_id="proj-a",
            content="fact a",
            fact_type="knowledge",
            metadata={"source": "autonomic_heartbeat", "ts": "1"},
        ),
        call(
            tenant_id="tenant-b",
            project_id="proj-b",
            content="fact b",
            fact_type="decision",
            metadata={"source": "autonomic_heartbeat", "ts": "2"},
        ),
    ]


@pytest.mark.asyncio
async def test_dynamic_semantic_space_stop_flushes_buffered_facts() -> None:
    manager = SimpleNamespace(store=AsyncMock())
    space = DynamicSemanticSpace(store=MagicMock(), manager=manager)

    space.autonomic_buffer.add(
        {
            "tenant_id": "tenant-stop",
            "project": "proj-stop",
            "content": "persist me",
            "fact_type": "knowledge",
            "timestamp": "stop-ts",
        }
    )

    await space.stop()

    manager.store.assert_awaited_once_with(
        tenant_id="tenant-stop",
        project_id="proj-stop",
        content="persist me",
        fact_type="knowledge",
        metadata={"source": "autonomic_heartbeat", "ts": "stop-ts"},
    )
    assert not space._active_flushes


@pytest.mark.asyncio
async def test_semantic_mutator_stop_shuts_down_pool_after_cancellation() -> None:
    space = DynamicSemanticSpace(store=MagicMock(), manager=SimpleNamespace(store=AsyncMock()))
    mutator = space.semantic_mutator
    mutator._worker_task = asyncio.create_task(asyncio.sleep(60))

    await mutator.stop()

    assert mutator._pool._shutdown is True
