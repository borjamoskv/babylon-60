from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.facts.manager import FactManager


class _NoopHaikuGuard:
    @staticmethod
    def enforce(content: str, metadata: dict[str, object]) -> None:
        return None


class _FakeCursor:
    def __init__(self, row):
        self._row = row

    async def fetchone(self):
        return self._row


class _FakeConn:
    def __init__(self, rows: dict[str, object | None] | None = None) -> None:
        self._rows = rows or {}
        self.executed: list[tuple[str, tuple]] = []
        self.commit_calls = 0

    async def execute(self, sql: str, params=()):
        self.executed.append((sql, params))
        row = None
        for prefix, value in self._rows.items():
            if sql.startswith(prefix):
                row = value
                break
        return _FakeCursor(row)

    async def commit(self) -> None:
        self.commit_calls += 1


class _DummyEngine:
    def __init__(self) -> None:
        self.memory = None
        self.embeddings = None
        self.search = AsyncMock(return_value=[])
        self.get_fact = AsyncMock(return_value=None)
        self.store_many = AsyncMock(return_value=[])

    def _resolve_tenant(self, tenant_id: str) -> str:
        return tenant_id


@pytest.mark.asyncio
async def test_fact_manager_rejects_thalamus_filtered_write(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _DummyEngine()
    engine.memory = SimpleNamespace(
        thalamus=SimpleNamespace(filter=AsyncMock(return_value=(False, "cooldown", None)))
    )
    manager = FactManager(engine)

    notify = AsyncMock()
    module = ModuleType("cortex.routes.notch_ws")
    module.notify_notch_pruning = notify
    monkeypatch.setitem(sys.modules, "cortex.routes.notch_ws", module)
    monkeypatch.setattr("cortex.facts.manager.HaikuGuard", _NoopHaikuGuard)

    with pytest.raises(ValueError, match="Thalamus: Fact rejected \\(cooldown\\)"):
        await manager.store(
            project="trust-core",
            content="This fact should be rejected before any persistence happens.",
            fact_type="knowledge",
            conn=_FakeConn(),
        )

    notify.assert_awaited_once()


@pytest.mark.asyncio
async def test_fact_manager_exact_duplicate_respects_return_created_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _DummyEngine()
    manager = FactManager(engine)
    conn = _FakeConn({"SELECT id FROM facts WHERE content = ? AND project = ? AND tenant_id = ?": (42,)})

    monkeypatch.setattr("cortex.facts.manager.HaikuGuard", _NoopHaikuGuard)
    monkeypatch.setattr("cortex.facts.manager.validate_content", lambda project, content, fact_type: content)

    result = await manager.store(
        project="trust-core",
        content="duplicate content",
        fact_type="knowledge",
        conn=conn,
        commit=False,
        _return_created=True,
    )

    assert result == (42, False)
    assert conn.commit_calls == 0
    assert any(sql.startswith("UPDATE facts SET updated_at = ? WHERE id = ?") for sql, _ in conn.executed)


@pytest.mark.asyncio
async def test_fact_manager_semantic_duplicate_commits_and_returns_created_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _DummyEngine()
    engine.embeddings = SimpleNamespace(embed_text=AsyncMock(return_value=[0.1, 0.2]))
    engine.search = AsyncMock(return_value=[SimpleNamespace(fact_id=99, score=0.95)])
    manager = FactManager(engine)
    conn = _FakeConn({"SELECT id FROM facts WHERE content = ? AND project = ? AND tenant_id = ?": None})

    monkeypatch.setattr("cortex.facts.manager.HaikuGuard", _NoopHaikuGuard)
    monkeypatch.setattr("cortex.facts.manager.validate_content", lambda project, content, fact_type: content)

    result = await manager.store(
        project="trust-core",
        content="near duplicate content",
        fact_type="knowledge",
        conn=conn,
        commit=True,
        _return_created=True,
    )

    assert result == (99, False)
    assert conn.commit_calls == 1
    assert any(sql.startswith("UPDATE facts SET updated_at = ? WHERE id = ?") for sql, _ in conn.executed)


@pytest.mark.asyncio
async def test_fact_manager_delegates_to_store_mixin_when_no_fast_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _DummyEngine()
    manager = FactManager(engine)
    conn = _FakeConn({"SELECT id FROM facts WHERE content = ? AND project = ? AND tenant_id = ?": None})

    monkeypatch.setattr("cortex.facts.manager.HaikuGuard", _NoopHaikuGuard)
    monkeypatch.setattr("cortex.facts.manager.validate_content", lambda project, content, fact_type: content)

    from cortex.engine.store_mixin import StoreMixin

    store_impl = AsyncMock(return_value=(7, True))
    monkeypatch.setattr(StoreMixin, "_store_impl", store_impl)

    result = await manager.store(
        project="trust-core",
        content="brand new content",
        fact_type="knowledge",
        conn=conn,
        commit=False,
        parent_decision_id=11,
        _return_created=True,
    )

    assert result == (7, True)
    store_impl.assert_awaited_once()
    assert store_impl.await_args.kwargs["parent_decision_id"] == 11
    assert store_impl.await_args.kwargs["run_precommit_post_hooks"] is True


@pytest.mark.asyncio
async def test_fact_manager_fails_closed_on_validation_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _DummyEngine()
    manager = FactManager(engine)
    conn = _FakeConn()

    monkeypatch.setattr(
        "cortex.facts.manager.validate_content",
        lambda project, content, fact_type: (_ for _ in ()).throw(ValueError("invalid content")),
    )

    from cortex.engine.store_mixin import StoreMixin

    store_impl = AsyncMock(return_value=(7, True))
    monkeypatch.setattr(StoreMixin, "_store_impl", store_impl)

    with pytest.raises(ValueError, match="invalid content"):
        await manager.store(
            project="trust-core",
            content="brand new content",
            fact_type="knowledge",
            conn=conn,
            commit=False,
        )

    store_impl.assert_not_awaited()


@pytest.mark.asyncio
async def test_fact_manager_fails_closed_on_runtime_ingestion_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _DummyEngine()
    engine.embeddings = SimpleNamespace(embed_text=AsyncMock(return_value=[0.1, 0.2]))
    engine.search = AsyncMock(side_effect=RuntimeError("search backend offline"))
    manager = FactManager(engine)
    conn = _FakeConn({"SELECT id FROM facts WHERE content = ? AND project = ? AND tenant_id = ?": None})

    monkeypatch.setattr("cortex.facts.manager.validate_content", lambda project, content, fact_type: content)

    from cortex.engine.store_mixin import StoreMixin

    store_impl = AsyncMock(return_value=(7, True))
    monkeypatch.setattr(StoreMixin, "_store_impl", store_impl)

    with pytest.raises(RuntimeError, match="FactManager ingestion checks failed"):
        await manager.store(
            project="trust-core",
            content="brand new content",
            fact_type="knowledge",
            conn=conn,
            commit=False,
        )

    store_impl.assert_not_awaited()


@pytest.mark.asyncio
async def test_fact_manager_get_fact_coerces_engine_dict_to_fact_model() -> None:
    engine = _DummyEngine()
    engine.get_fact = AsyncMock(
        return_value={
            "id": 5,
            "tenant_id": "tenant-a",
            "project": "trust-core",
            "content": "stored fact",
            "fact_type": "knowledge",
            "unknown_field": "ignored",
        }
    )
    manager = FactManager(engine)

    fact = await manager.get_fact(5)

    assert fact is not None
    assert fact.id == 5
    assert fact.project == "trust-core"
    assert not hasattr(fact, "unknown_field")


@pytest.mark.asyncio
async def test_fact_manager_store_many_empty_raises_without_touching_engine() -> None:
    engine = _DummyEngine()
    manager = FactManager(engine)

    with pytest.raises(ValueError, match="Facts list cannot be empty"):
        await manager.store_many([])

    engine.store_many.assert_not_awaited()
