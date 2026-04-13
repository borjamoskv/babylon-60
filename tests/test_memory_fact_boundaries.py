from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.memory.hdc.store import HDCVectorStoreL2
from cortex.memory.memory_compression import _snapshot_to_fact, compress_and_store
from cortex.memory.models import CortexFactModel, EpisodicSnapshot, MemoryEntry, MemoryEvent
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2


def _make_legacy_entry() -> MemoryEntry:
    return MemoryEntry(content="legacy entry", project="proj-1")


def _make_snapshot() -> EpisodicSnapshot:
    return EpisodicSnapshot(
        summary="episodic snapshot",
        vector_embedding=[0.1, 0.2],
        linked_events=["evt-1"],
        session_id="sess-1",
        tenant_id="tenant-1",
    )


def _make_events() -> list[MemoryEvent]:
    return [
        MemoryEvent(
            event_id="evt-1",
            role="user",
            content="first interaction",
            token_count=3,
            session_id="sess-1",
            tenant_id="tenant-1",
        ),
        MemoryEvent(
            event_id="evt-2",
            role="assistant",
            content="second interaction",
            token_count=5,
            session_id="sess-1",
            tenant_id="tenant-1",
        ),
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("artifact", [_make_legacy_entry(), _make_snapshot()])
async def test_sovereign_store_rejects_non_fact_artifacts(artifact: object) -> None:
    store = object.__new__(SovereignVectorStoreL2)

    with pytest.raises(TypeError, match="CortexFactModel"):
        await store.memorize(artifact)  # type: ignore[arg-type]


@pytest.mark.asyncio
@pytest.mark.parametrize("artifact", [_make_legacy_entry(), _make_snapshot()])
async def test_hdc_store_rejects_non_fact_artifacts(artifact: object) -> None:
    store = object.__new__(HDCVectorStoreL2)

    with pytest.raises(TypeError, match="CortexFactModel"):
        await store.memorize(artifact)  # type: ignore[arg-type]


def test_snapshot_to_fact_requires_vector_embedding() -> None:
    snapshot = EpisodicSnapshot(
        summary="episodic snapshot",
        vector_embedding=[],
        linked_events=["evt-1"],
        session_id="sess-1",
        tenant_id="tenant-1",
    )

    with pytest.raises(ValueError, match="vector_embedding"):
        _snapshot_to_fact(
            snapshot,
            project_id="proj-1",
            compression_mode="raw",
        )


@pytest.mark.asyncio
async def test_compress_and_store_marks_sovereign_episode_artifacts() -> None:
    class SovereignVectorStoreL2:
        def __init__(self) -> None:
            self.memorize = AsyncMock()

    l2 = SovereignVectorStoreL2()
    hdc = SimpleNamespace(memorize=AsyncMock())
    manager = SimpleNamespace(
        _router=None,
        _encoder=SimpleNamespace(encode=AsyncMock(return_value=[0.1, 0.2])),
        _l2=l2,
        _hdc=hdc,
    )

    await compress_and_store(
        manager,
        _make_events(),
        session_id="sess-1",
        tenant_id="tenant-1",
        project_id="proj-1",
    )

    l2.memorize.assert_awaited_once()
    stored = l2.memorize.await_args.args[0]
    assert isinstance(stored, CortexFactModel)
    assert stored.cognitive_layer == "episodic"
    assert stored.category == "episodic"
    assert stored.metadata["memory_artifact_kind"] == "episodic_snapshot"
    assert stored.metadata["type"] == "episodic_snapshot"
    assert stored.metadata["linked_events"] == ["evt-1", "evt-2"]
    assert stored.metadata["event_count"] == 2
    assert hdc.memorize.await_args.args[0] is stored


@pytest.mark.asyncio
async def test_compress_and_store_marks_legacy_episode_artifacts() -> None:
    class LegacyStoreDouble:
        def __init__(self) -> None:
            self.memorize = AsyncMock()

    l2 = LegacyStoreDouble()
    manager = SimpleNamespace(
        _router=None,
        _encoder=SimpleNamespace(encode=AsyncMock(return_value=[0.1, 0.2])),
        _l2=l2,
        _hdc=None,
    )

    await compress_and_store(
        manager,
        _make_events(),
        session_id="sess-1",
        tenant_id="tenant-1",
        project_id="proj-1",
    )

    l2.memorize.assert_awaited_once()
    stored = l2.memorize.await_args.args[0]
    assert isinstance(stored, MemoryEntry)
    assert stored.project == "proj-1"
    assert stored.metadata["memory_artifact_kind"] == "episodic_snapshot"
    assert stored.metadata["type"] == "episodic_snapshot"
    assert stored.metadata["tenant_id"] == "tenant-1"
    assert stored.metadata["linked_events"] == ["evt-1", "evt-2"]
