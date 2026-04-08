from __future__ import annotations

import json

from cortex.extensions.daemon import state as daemon_state_module
from cortex.extensions.daemon.state import DaemonState, HotMemory


def test_hot_memory_ignores_writes_when_capacity_is_non_positive() -> None:
    memory = HotMemory(capacity=0)

    memory.store("a", 1)

    assert memory.retrieve("a") is None
    assert memory.cache == {}


def test_daemon_state_save_and_load_round_trip(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(daemon_state_module, "CORTEX_ROOT", tmp_path)

    state = DaemonState()
    state.daemons["cortex"]["handshake"] = "remote"
    state.daemons["gidatu"]["status"] = "online"

    state.save_state()

    handoff = tmp_path / "handoff.json"
    assert handoff.exists()
    data = json.loads(handoff.read_text(encoding="utf-8"))
    assert data["cortex"]["handshake"] == "remote"
    assert data["gidatu"]["status"] == "online"

    restored = DaemonState()
    assert restored.load_state() is True
    assert restored.daemons["cortex"]["handshake"] == "remote"
    assert restored.daemons["gidatu"]["status"] == "online"
