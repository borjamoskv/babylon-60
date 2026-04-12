# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""CORTEX v6.0 — Pulse-Driven Observability (Ω₄: Aesthetic Integrity).

True observability operates on the pulse (DurableSignalBus) instead of the corpse (post-hoc logs).
This module provides a sovereign registry that derives system metrics directly from
L1 consciousness signals.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from cortex.extensions.signals.bus import DurableSignalBus

logger = logging.getLogger("cortex.telemetry.pulse")

_DEFAULT_EVENT_WINDOW_S = 300.0
_DEFAULT_PULSE_WINDOW_S = 60.0
_MAX_RECENT_EVENTS = 4096


@dataclass()
class PulseMetric:
    """A metric derived from the system pulse."""

    name: str
    value: float = 0.0
    labels: dict[str, str] = field(default_factory=dict)
    last_update: float = field(default_factory=time.time)
    source: str = "pulse"


@dataclass()
class PulseEvent:
    """A recent event used to derive kinetic telemetry."""

    event_type: str
    source: str
    timestamp: float


class PulseRegistry:
    """Sovereign Metrics Registry driven by the SignalBus pulse.

    Redesigns the data flow by preferring direct signals over manual increments.
    """

    def __init__(
        self,
        signal_bus: Optional[DurableSignalBus] = None,
        *,
        event_window_s: float = _DEFAULT_EVENT_WINDOW_S,
        max_recent_events: int = _MAX_RECENT_EVENTS,
    ) -> None:
        self._signal_bus = signal_bus
        self._metrics: dict[str, PulseMetric] = {}
        self._lock = threading.RLock()
        self._ghost_metrics: set[str] = set()  # Metrics flagged as "shadows"
        self._recent_events: deque[PulseEvent] = deque(maxlen=max_recent_events)
        self._event_window_s = event_window_s
        self._is_active = False

    def set_bus(self, signal_bus: DurableSignalBus) -> None:
        """Inject the SignalBus pulse source."""
        self._signal_bus = signal_bus

    async def start_observer(self, interval: float = 1.0) -> None:
        """Starts the pulse observer loop."""
        if self._is_active or not self._signal_bus:
            return
        self._is_active = True
        logger.info("💓 [PULSE] Observer ignited. Redesigning data flow to reality.")

        while self._is_active:
            try:
                # Poll L1 signals
                signals = self._signal_bus.poll(consumer="pulse_observer", limit=100)
                if signals:
                    with self._lock:
                        for signal in signals:
                            self._process_signal(signal)
            except Exception as e:  # noqa: BLE001 — pulse observer loop must not crash
                logger.error("[PULSE] Pulse scan failed: %s", e)
            await asyncio.sleep(interval)

    def _process_signal(self, signal: Any) -> None:
        """Infers metrics from a pulse signal."""
        event_type = signal.event_type
        source = getattr(signal, "source", "unknown")
        now = time.time()

        self._record_event(event_type, source, now)

        # 1. Automatic metric derivation from event_type
        # Patterns:
        #   'error:*' -> counter
        #   'heartbeat:*' -> gauge
        #   'consensus:*' -> counter

        if event_type.startswith("error:"):
            metric_name = f"cortex_{event_type.replace(':', '_')}_total"
            self.inc(metric_name, labels={"source": source})
        elif event_type == "heartbeat:pulse":
            drift = signal.payload.get("semantic_drift", 0.0)
            self.set_gauge("cortex_semantic_drift", drift)
        elif event_type.startswith("consensus:"):
            self.inc("cortex_consensus_ops_total", labels={"op": event_type.split(":")[1]})

        self.inc(
            "cortex_pulse_events_total",
            labels={"family": self._event_family(event_type)},
        )

        # 2. Shadow Detection: If we see a signal for something that was manually logged,
        # we flag the manual log as a "ghost".
        self._ghost_metrics.add(event_type)

    @staticmethod
    def _event_family(event_type: str) -> str:
        return event_type.split(":", 1)[0]

    def _record_event(self, event_type: str, source: str, now: float) -> None:
        self._recent_events.append(PulseEvent(event_type=event_type, source=source, timestamp=now))
        self._prune_events(now)
        self._refresh_kinetic_gauges(now)

    def _prune_events(self, now: float) -> None:
        cutoff = now - self._event_window_s
        while self._recent_events and self._recent_events[0].timestamp < cutoff:
            self._recent_events.popleft()

    def _events_in_window(self, now: float, window_s: float) -> list[PulseEvent]:
        cutoff = now - window_s
        return [event for event in self._recent_events if event.timestamp >= cutoff]

    def _kinetic_snapshot(self, now: float, window_s: float) -> dict[str, Any]:
        events = self._events_in_window(now, window_s)
        event_count = len(events)
        event_counter = Counter(event.event_type for event in events)
        active_sources = {event.source for event in events}
        error_count = sum(1 for event in events if event.event_type.startswith("error:"))
        consensus_count = sum(1 for event in events if event.event_type.startswith("consensus:"))

        return {
            "window_seconds": window_s,
            "event_count": event_count,
            "event_rate_hz": event_count / window_s if window_s > 0 else 0.0,
            "events_per_minute": (event_count * 60.0) / window_s if window_s > 0 else 0.0,
            "error_rate_hz": error_count / window_s if window_s > 0 else 0.0,
            "consensus_rate_hz": consensus_count / window_s if window_s > 0 else 0.0,
            "active_sources": len(active_sources),
            "hot_signals": [
                {"event_type": event_type, "count": count}
                for event_type, count in event_counter.most_common(5)
            ],
        }

    def _refresh_kinetic_gauges(self, now: float) -> None:
        snapshot = self._kinetic_snapshot(now, _DEFAULT_PULSE_WINDOW_S)
        self.set_gauge("cortex_pulse_event_rate_hz", snapshot["event_rate_hz"])
        self.set_gauge("cortex_pulse_error_rate_hz", snapshot["error_rate_hz"])
        self.set_gauge("cortex_pulse_consensus_rate_hz", snapshot["consensus_rate_hz"])
        self.set_gauge("cortex_pulse_active_sources", float(snapshot["active_sources"]))

    def inc(self, name: str, value: float = 1.0, labels: Optional[dict[str, str]] = None) -> None:
        """Increments a pulse-driven counter."""
        key = self._gen_key(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = PulseMetric(name=name, labels=labels or {})
            self._metrics[key].value += value
            self._metrics[key].last_update = time.time()

    def set_gauge(self, name: str, value: float, labels: Optional[dict[str, str]] = None) -> None:
        """Sets a pulse-driven gauge."""
        key = self._gen_key(name, labels)
        with self._lock:
            if key not in self._metrics:
                self._metrics[key] = PulseMetric(name=name, labels=labels or {})
            self._metrics[key].value = value
            self._metrics[key].last_update = time.time()

    def _gen_key(self, name: str, labels: Optional[dict[str, str]]) -> str:
        if not labels:
            return name
        l_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{l_str}}}"

    def get_pulse(self, window_s: float = _DEFAULT_PULSE_WINDOW_S) -> dict[str, Any]:
        """Returns the current state of the pulse."""
        with self._lock:
            now = time.time()
            kinetic = self._kinetic_snapshot(now, window_s)
            return {
                "active_metrics": len(self._metrics),
                "shadow_ghosts": list(self._ghost_metrics),
                "pulse_rate": sum(
                    1
                    for m in self._metrics.values()
                    if now - m.last_update < _DEFAULT_PULSE_WINDOW_S
                ),
                **kinetic,
            }


# Global Pulse Registry (v6)
PULSE = PulseRegistry()
