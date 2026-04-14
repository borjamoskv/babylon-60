from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from cortex.services.tips_engine import TipCategory, TipsEngine


class _FakeCursor:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    async def fetchall(self) -> list[tuple[object, ...]]:
        return self._rows


class _FakeConn:
    def __init__(self, rows_by_fact_type: dict[str, list[tuple[object, ...]]]) -> None:
        self._rows_by_fact_type = rows_by_fact_type

    async def execute(self, _sql: str, params: tuple[object, ...]) -> _FakeCursor:
        fact_type = params[0]
        rows = self._rows_by_fact_type.get(str(fact_type), [])
        return _FakeCursor(rows)


class _FakeSession:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> _FakeConn:
        return self._conn

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.asyncio
async def test_refresh_dynamic_uses_session_instead_of_get_conn(monkeypatch) -> None:
    """Regression test for the deprecated connection path."""

    monkeypatch.setattr(
        "cortex.storage.classifier.classify_content",
        lambda _content: SimpleNamespace(is_sensitive=False),
    )

    conn = _FakeConn(
        {
            "decision": [(1, "proj-alpha", "Decision tip")],
            "error": [],
            "bridge": [],
        }
    )
    engine = Mock()
    engine.session = Mock(return_value=_FakeSession(conn))
    engine.get_conn = Mock(side_effect=AssertionError("get_conn() must not be called"))

    tips_engine = TipsEngine(engine, include_dynamic=True, max_dynamic=3)

    await tips_engine._refresh_dynamic()

    engine.session.assert_called_once_with()
    engine.get_conn.assert_not_called()
    assert tips_engine._dynamic_cache
    assert tips_engine._dynamic_cache[0].category is TipCategory.MEMORY
