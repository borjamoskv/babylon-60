from __future__ import annotations

from types import SimpleNamespace

from cortex.telemetry.pulse import PulseRegistry


def _signal(event_type: str, *, source: str = "unit", payload: dict | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        event_type=event_type,
        source=source,
        payload=payload or {},
    )


def test_pulse_registry_derives_kinetic_rates(monkeypatch) -> None:
    clock = {"now": 100.0}
    monkeypatch.setattr("cortex.telemetry.pulse.time.time", lambda: clock["now"])
    registry = PulseRegistry(event_window_s=120.0)

    registry._process_signal(_signal("error:consensus:agent_not_found", source="consensus"))
    clock["now"] = 110.0
    registry._process_signal(_signal("consensus:vote_cast", source="consensus"))
    clock["now"] = 120.0
    registry._process_signal(
        _signal("heartbeat:pulse", source="daemon", payload={"semantic_drift": 0.25})
    )

    pulse = registry.get_pulse(window_s=60.0)

    assert pulse["event_count"] == 3
    assert pulse["active_sources"] == 2
    assert abs(pulse["event_rate_hz"] - (3 / 60.0)) < 1e-9
    assert abs(pulse["error_rate_hz"] - (1 / 60.0)) < 1e-9
    assert abs(pulse["consensus_rate_hz"] - (1 / 60.0)) < 1e-9
    assert pulse["hot_signals"][0]["count"] == 1


def test_pulse_registry_prunes_events_outside_retention(monkeypatch) -> None:
    clock = {"now": 100.0}
    monkeypatch.setattr("cortex.telemetry.pulse.time.time", lambda: clock["now"])
    registry = PulseRegistry(event_window_s=30.0)

    registry._process_signal(_signal("error:one"))
    clock["now"] = 140.0
    registry._process_signal(_signal("error:two"))

    pulse = registry.get_pulse(window_s=60.0)

    assert pulse["event_count"] == 1
    assert pulse["hot_signals"] == [{"event_type": "error:two", "count": 1}]


def test_pulse_registry_emits_family_counter_and_kinetic_gauges(monkeypatch) -> None:
    monkeypatch.setattr("cortex.telemetry.pulse.time.time", lambda: 200.0)
    registry = PulseRegistry()

    registry._process_signal(_signal("error:io_timeout", source="io"))

    assert "cortex_pulse_events_total{family=error}" in registry._metrics
    assert "cortex_pulse_event_rate_hz" in registry._metrics
    assert "cortex_pulse_error_rate_hz" in registry._metrics
    assert "cortex_pulse_active_sources" in registry._metrics
