from __future__ import annotations

from cortex.utils.context_formatter import compact_session


class _Rows:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def fetchall(self) -> list[tuple]:
        return self._rows


class _Connection:
    def __init__(self, rows: list[tuple]) -> None:
        self.rows = rows
        self.seen_params: tuple | None = None

    def execute(self, _sql: str, params: tuple) -> _Rows:
        self.seen_params = params
        return _Rows(self.rows)


class _Engine:
    def __init__(self, rows: list[tuple]) -> None:
        self.connection = _Connection(rows)

    def _get_sync_conn(self) -> _Connection:
        return self.connection


def test_compact_session_returns_empty_context_when_no_active_facts() -> None:
    engine = _Engine([])

    output = compact_session(engine, "cortex", max_facts=7)

    assert engine.connection.seen_params == ("cortex", 7)
    assert output == "# cortex\n\nNo active facts.\n"


def test_compact_session_groups_known_types_before_unknown_types_and_truncates() -> None:
    long_content = "x" * 250
    rows = [
        (1, "metric body", "metric", "tag", 0.1, "2026-01-03"),
        (2, long_content, "decision", "tag", 0.9, "2026-01-02"),
        (3, "knowledge body", "knowledge", "tag", 0.8, "2026-01-01"),
    ]
    engine = _Engine(rows)

    output = compact_session(engine, "cortex", max_facts=3)

    assert output.index("## Decision (1)") < output.index("## Knowledge (1)")
    assert output.index("## Knowledge (1)") < output.index("## Metric (1)")
    assert f"- {long_content[:200]}" in output
    assert long_content[:201] not in output
