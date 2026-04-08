from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace

import pytest

from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.store import LedgerStore
from cortex.ledger.writer import LedgerWriter
from cortex.mac_maestro.executor import MaestroExecutor
from cortex.mac_maestro.intent import MacAction, MacIntent


def _make_executor(tmp_path) -> MaestroExecutor:
    db = tmp_path / "ledger.db"
    store = LedgerStore(db)
    queue = EnrichmentQueue(store)
    writer = LedgerWriter(store, queue)
    return MaestroExecutor(writer)


def _signal_rows(db_path) -> list[tuple[str, str]]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT event_type, payload FROM signals ORDER BY id").fetchall()
    finally:
        conn.close()


def test_executor_emits_safety_gate_signal(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    executor = _make_executor(tmp_path)
    monkeypatch.setattr("cortex.mac_maestro.executor.SDK_AVAILABLE", True)

    class _Workflow:
        def __init__(self, bundle_id: str) -> None:
            self.run_id = "run-safety"

        def execute_action(self, sdk_action, apply_safety_gate: bool = True) -> bool:
            return True

    monkeypatch.setattr(
        "cortex.mac_maestro.executor.MacMaestroWorkflow", _Workflow, raising=False
    )
    monkeypatch.setattr(
        executor, "_convert_action", lambda action: SimpleNamespace(vector="B")
    )
    monkeypatch.setattr(
        executor,
        "_ensure_action_access",
        lambda action, sdk_action: (_ for _ in ()).throw(PermissionError("accessibility denied")),
    )

    intent = MacIntent(
        goal="Click save",
        correlation_id="corr-1",
        actions=[MacAction(action="click", app="com.apple.TextEdit", role="AXButton", title="Save")],
    )

    executor.execute_intent(intent)
    rows = _signal_rows(executor.ledger_writer.store.db_path)

    assert len(rows) == 1
    assert rows[0][0] == "mac_maestro:safety_gate_blocked"
    payload = json.loads(rows[0][1])
    assert payload["correlation_id"] == "corr-1"
    assert payload["action"] == "click"


def test_executor_emits_verification_failed_signal(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executor = _make_executor(tmp_path)
    monkeypatch.setattr("cortex.mac_maestro.executor.SDK_AVAILABLE", True)

    class _Workflow:
        def __init__(self, bundle_id: str) -> None:
            self.run_id = "run-verify"

        def execute_action(self, sdk_action, apply_safety_gate: bool = True) -> bool:
            return True

    monkeypatch.setattr(
        "cortex.mac_maestro.executor.MacMaestroWorkflow", _Workflow, raising=False
    )
    monkeypatch.setattr(
        executor, "_convert_action", lambda action: SimpleNamespace(vector="B")
    )
    monkeypatch.setattr(executor, "_ensure_action_access", lambda action, sdk_action: None)

    intent = MacIntent(
        goal="Click save",
        trace_id="trace-1",
        actions=[MacAction(action="click", app="com.apple.TextEdit", role="AXButton", title="Save")],
    )
    oracle = SimpleNamespace(verify=lambda: SimpleNamespace(verified=False, reason="Toast missing"))

    executor.execute_intent(intent, oracle=oracle)
    rows = _signal_rows(executor.ledger_writer.store.db_path)

    assert len(rows) == 1
    assert rows[0][0] == "mac_maestro:verification_failed"
    payload = json.loads(rows[0][1])
    assert payload["trace_id"] == "trace-1"
    assert payload["verification_error"] == "Toast missing"


def test_executor_emits_slow_action_signal(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    executor = _make_executor(tmp_path)
    monkeypatch.setattr("cortex.mac_maestro.executor.SDK_AVAILABLE", True)

    class _Workflow:
        def __init__(self, bundle_id: str) -> None:
            self.run_id = "run-slow"

        def execute_action(self, sdk_action, apply_safety_gate: bool = True) -> bool:
            return True

    perf_counter = iter([10.0, 11.8])
    monkeypatch.setattr(
        "cortex.mac_maestro.executor.MacMaestroWorkflow", _Workflow, raising=False
    )
    monkeypatch.setattr(
        executor, "_convert_action", lambda action: SimpleNamespace(vector="B")
    )
    monkeypatch.setattr(executor, "_ensure_action_access", lambda action, sdk_action: None)
    monkeypatch.setattr("cortex.mac_maestro.executor.time.perf_counter", lambda: next(perf_counter))

    intent = MacIntent(
        goal="Open menu",
        actions=[MacAction(action="click", app="com.apple.TextEdit", role="AXButton", title="Open")],
    )

    executor.execute_intent(intent)
    rows = _signal_rows(executor.ledger_writer.store.db_path)

    assert len(rows) == 1
    assert rows[0][0] == "mac_maestro:action_slow"
    payload = json.loads(rows[0][1])
    assert payload["latency_ms"] >= 1500
