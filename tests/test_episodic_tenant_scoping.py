from __future__ import annotations

from types import SimpleNamespace

import aiosqlite
import pytest

from cortex.memory.episodic import CausalTracer


async def _build_conn() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(":memory:")
    await conn.execute(
        """
        CREATE TABLE facts (
            id INTEGER,
            tenant_id TEXT,
            project TEXT,
            content TEXT,
            fact_type TEXT,
            parent_decision_id INTEGER
        )
        """
    )
    await conn.commit()
    return conn


@pytest.mark.asyncio
async def test_trace_episode_filters_recursive_chain_by_tenant() -> None:
    conn = await _build_conn()
    await conn.executemany(
        "INSERT INTO facts (id, tenant_id, project, content, fact_type, parent_decision_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, "tenant-a", "proj-a", "root-a", "decision", None),
            (2, "tenant-a", "proj-a", "child-a", "knowledge", 1),
            (1, "tenant-b", "proj-b", "root-b", "decision", None),
            (3, "tenant-b", "proj-b", "child-b", "knowledge", 1),
        ],
    )
    await conn.commit()

    tracer = CausalTracer(conn)

    episode = await tracer.trace_episode(2, tenant_id="tenant-a")

    assert episode.project == "proj-a"
    assert [node["id"] for node in episode.fact_chain] == [1, 2]
    assert all(node["content"].endswith("-a") for node in episode.fact_chain)

    await conn.close()


@pytest.mark.asyncio
async def test_recall_episode_filters_search_and_trace_by_tenant() -> None:
    conn = await _build_conn()
    await conn.executemany(
        "INSERT INTO facts (id, tenant_id, project, content, fact_type, parent_decision_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (10, "tenant-a", "shared", "migration failed in api", "decision", None),
            (11, "tenant-a", "shared", "fix api migration", "knowledge", 10),
            (20, "tenant-b", "shared", "migration failed in billing", "decision", None),
            (21, "tenant-b", "shared", "fix billing migration", "knowledge", 20),
        ],
    )
    await conn.commit()

    tracer = CausalTracer(conn)

    episodes = await tracer.recall_episode("migration", project="shared", tenant_id="tenant-a")

    assert len(episodes) == 1
    assert episodes[0].project == "shared"
    assert [node["id"] for node in episodes[0].fact_chain] == [10, 11]

    await conn.close()


@pytest.mark.asyncio
async def test_engine_trace_episode_forwards_tenant_id(monkeypatch) -> None:
    from cortex.engine import CortexEngine

    calls: list[tuple[int, int | None, str]] = []

    class DummyTracer:
        def __init__(self, _conn) -> None:
            pass

        async def trace_episode(
            self,
            fact_id: int,
            max_depth: int | None = None,
            tenant_id: str = "default",
        ) -> SimpleNamespace:
            calls.append((fact_id, max_depth, tenant_id))
            return SimpleNamespace(root_fact_id=fact_id, fact_chain=[], depth=0, entropy_density=0.0)

    class DummySession:
        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr("cortex.memory.episodic.CausalTracer", DummyTracer)

    engine = CortexEngine(":memory:", auto_embed=False)
    monkeypatch.setattr(engine, "session", lambda: DummySession())

    result = await engine.trace_episode(7, max_depth=4, tenant_id="tenant-z")

    assert result.root_fact_id == 7
    assert calls == [(7, 4, "tenant-z")]
