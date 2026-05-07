from __future__ import annotations

import logging
from typing import Any

from cortex.engine.storage_guard import GuardViolation
from cortex.extensions.daemon.entropic_wake import EntropicWakeDaemon
from cortex.extensions.daemon.frontier import FrontierDaemon
from cortex.extensions.daemon.health_loop import HealthLoop


class _CapturingSyncStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def store_sync(self, **kwargs: Any) -> int:
        self.calls.append(kwargs)
        return len(self.calls)


class _RejectingSyncStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def store_sync(self, **kwargs: Any) -> int:
        self.calls.append(kwargs)
        raise GuardViolation("TEST_GUARD", "daemon payload rejected by storage guard")


def test_health_loop_snapshot_uses_tenant_scoped_canonical_store() -> None:
    engine = _CapturingSyncStore()
    data = {"score": 91.25, "grade": "A", "metrics": []}

    HealthLoop().persist_snapshot(engine, data)

    assert engine.calls == [
        {
            "tenant_id": "default",
            "project": "cortex",
            "content": "Health snapshot: 91.25/100 (A)",
            "fact_type": "bridge",
            "source": "daemon:health",
            "tags": ["health", "snapshot", "A"],
            "meta": data,
            "confidence": "C5",
        }
    ]


def test_entropic_wake_logs_guard_rejection_without_silent_success(caplog) -> None:
    engine = _RejectingSyncStore()

    with caplog.at_level(logging.ERROR, logger="cortex.extensions.daemon.entropic_wake"):
        EntropicWakeDaemon(engine=engine)._log_action_to_cortex("unsafe-target")

    assert len(engine.calls) == 1
    assert engine.calls[0]["tenant_id"] == "default"
    assert engine.calls[0]["source"] == "entropic-wake-daemon"
    assert "Failed to log to cortex DB" in caplog.text
    assert "TEST_GUARD" in caplog.text


def test_frontier_daemon_logs_guard_rejection_without_silent_success(caplog) -> None:
    engine = _RejectingSyncStore()

    with caplog.at_level(logging.ERROR, logger="cortex.extensions.daemon.frontier"):
        FrontierDaemon(engine=engine)._log_evolution("ingestion", "unsafe payload")

    assert len(engine.calls) == 1
    assert engine.calls[0]["tenant_id"] == "default"
    assert engine.calls[0]["source"] == "frontier-daemon"
    assert "[FRONTIER] Failed to log evolution" in caplog.text
    assert "TEST_GUARD" in caplog.text
