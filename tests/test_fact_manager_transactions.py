from __future__ import annotations

from typing import Any

from cortex.facts.manager import FactManager


class _Cursor:
    def __init__(self, row: tuple[int] | None = None) -> None:
        self._row = row

    async def fetchone(self) -> tuple[int] | None:
        return self._row


class _DuplicateConnection:
    def __init__(self, duplicate_row: tuple[int] | None = (41,)) -> None:
        self._duplicate_row = duplicate_row
        self.commits = 0
        self.updates: list[tuple[Any, ...]] = []

    async def execute(self, sql: str, params: tuple[Any, ...]) -> _Cursor:
        if sql.startswith("SELECT id FROM facts"):
            return _Cursor(self._duplicate_row)
        if sql.startswith("UPDATE facts SET updated_at"):
            self.updates.append(params)
            return _Cursor()
        raise AssertionError(f"unexpected SQL: {sql}")

    async def commit(self) -> None:
        self.commits += 1


class _Engine:
    memory = None

    def _resolve_tenant(self, tenant_id: str) -> str:
        return tenant_id


class _Embeddings:
    async def embed_text(self, content: str) -> list[float]:
        return [1.0]


class _SemanticResult:
    fact_id = 84
    score = 0.95


class _SemanticEngine(_Engine):
    embeddings = _Embeddings()

    async def search(
        self,
        *,
        query: str,
        tenant_id: str,
        project: str,
        top_k: int,
    ) -> list[_SemanticResult]:
        return [_SemanticResult()]


async def test_duplicate_fact_manager_store_respects_commit_false() -> None:
    conn = _DuplicateConnection()
    manager = FactManager(_Engine())  # type: ignore[arg-type]

    fact_id = await manager.store(
        project="batch",
        content="Duplicate content should not commit inside a larger batch.",
        tenant_id="tenant-alpha",
        fact_type="knowledge",
        source="agent:test",
        commit=False,
        conn=conn,
    )

    assert fact_id == 41
    assert conn.updates
    assert conn.commits == 0


async def test_duplicate_fact_manager_store_commits_standalone_write() -> None:
    conn = _DuplicateConnection()
    manager = FactManager(_Engine())  # type: ignore[arg-type]

    fact_id = await manager.store(
        project="batch",
        content="Duplicate content should commit for standalone store calls.",
        tenant_id="tenant-alpha",
        fact_type="knowledge",
        source="agent:test",
        commit=True,
        conn=conn,
    )

    assert fact_id == 41
    assert conn.updates
    assert conn.commits == 1


async def test_semantic_duplicate_fact_manager_store_respects_commit_false() -> None:
    conn = _DuplicateConnection(duplicate_row=None)
    manager = FactManager(_SemanticEngine())  # type: ignore[arg-type]

    fact_id = await manager.store(
        project="batch",
        content="Semantically duplicate content should not commit inside a batch.",
        tenant_id="tenant-alpha",
        fact_type="knowledge",
        source="agent:test",
        commit=False,
        conn=conn,
    )

    assert fact_id == 84
    assert conn.updates
    assert conn.commits == 0
