# [C5-REAL] Exergy-Maximized
"""Replay Determinism Proof — CI Gate.

Proves: given an identical event trace, two independent replays
produce byte-identical final hashes. This is the formal contract
for the CORTEX verifiable execution substrate.

If this test fails, the runtime has lost determinism and NO merge
is permitted until the regression is resolved.
"""

from __future__ import annotations

import pytest

from cortex.runtime.system_state import SystemStateVector, StateEvent
from cortex.runtime.replay import ReplayEngine, ReplayResult


# ── Fixed canonical event trace ──────────────────────────────────

CANONICAL_TRACE: list[dict] = [
    {"event_type": "agent.registered", "source": "agent:health-monitor", "payload": {"agent_id": "health-monitor"}},
    {"event_type": "agent.registered", "source": "agent:task-worker", "payload": {"agent_id": "task-worker"}},
    {"event_type": "agent.started", "source": "agent:health-monitor", "payload": {}},
    {"event_type": "agent.started", "source": "agent:task-worker", "payload": {}},
    {"event_type": "task.submitted", "source": "system", "payload": {"task_id": "t-001", "description": "determinism proof"}},
    {"event_type": "task.completed", "source": "agent:task-worker", "payload": {"task_id": "t-001", "result": "ok"}},
    {"event_type": "system.error", "source": "agent:health-monitor", "payload": {"error": "synthetic-fault"}},
    {"event_type": "system.recovery", "source": "system", "payload": {}},
    {"event_type": "task.submitted", "source": "system", "payload": {"task_id": "t-002", "description": "post-recovery task"}},
    {"event_type": "task.completed", "source": "agent:task-worker", "payload": {"task_id": "t-002", "result": "ok"}},
    {"event_type": "agent.stopped", "source": "agent:task-worker", "payload": {}},
    {"event_type": "agent.stopped", "source": "agent:health-monitor", "payload": {}},
]


def _build_ledger_from_trace(trace: list[dict]) -> list[StateEvent]:
    """Run a canonical trace through a fresh StateVector, capture the ledger."""
    sv = SystemStateVector()
    for entry in trace:
        sv.apply(
            event_type=entry["event_type"],
            source=entry["source"],
            payload=entry.get("payload", {}),
        )
    return list(sv._ledger)


# ═══════════════════════════════════════════════════════════════════
# TEST SUITE
# ═══════════════════════════════════════════════════════════════════


class TestReplayIdentity:
    """Core contract: replay(trace) == replay(trace), always."""

    def test_replay_identity_two_runs(self):
        """Two replays of identical trace produce identical final hashes."""
        ledger = _build_ledger_from_trace(CANONICAL_TRACE)
        engine = ReplayEngine()

        r1 = engine.replay(ledger)
        r2 = engine.replay(ledger)

        assert r1.success, f"Run 1 failed: {r1.errors}"
        assert r2.success, f"Run 2 failed: {r2.errors}"
        assert r1.final_hash == r2.final_hash, (
            f"DETERMINISM VIOLATION: r1={r1.final_hash[:16]}... "
            f"r2={r2.final_hash[:16]}..."
        )
        assert r1.ticks_replayed == r2.ticks_replayed == len(CANONICAL_TRACE)

    def test_replay_identity_n_runs(self):
        """N replays all converge to same hash (uses verify_determinism)."""
        ledger = _build_ledger_from_trace(CANONICAL_TRACE)
        engine = ReplayEngine()
        assert engine.verify_determinism(ledger, runs=5), "Determinism failed across 5 runs"

    def test_replay_hash_matches_original(self):
        """Replay final hash matches the original StateVector hash."""
        sv = SystemStateVector()
        for entry in CANONICAL_TRACE:
            sv.apply(
                event_type=entry["event_type"],
                source=entry["source"],
                payload=entry.get("payload", {}),
            )
        original_hash = sv.hash

        ledger = list(sv._ledger)
        engine = ReplayEngine()
        result = engine.replay(ledger, expected_final_hash=original_hash)

        assert result.success, f"Replay errors: {result.errors}"
        assert result.hash_match, (
            f"Hash mismatch: original={original_hash[:16]}... "
            f"replayed={result.final_hash[:16]}..."
        )


class TestReplayHashChain:
    """Verify hash chain integrity survives replay."""

    def test_hash_chain_valid_after_replay(self):
        """Replayed StateVector maintains valid hash chain."""
        ledger = _build_ledger_from_trace(CANONICAL_TRACE)
        engine = ReplayEngine()
        result = engine.replay(ledger)

        assert result.success
        assert result.hash_match
        # The replayed state must have an intact chain
        assert result.final_hash != "", "Final hash cannot be empty"

    def test_divergence_detected_on_tampered_event(self):
        """Tampering with a single event causes divergence detection."""
        ledger = _build_ledger_from_trace(CANONICAL_TRACE)

        # Tamper: corrupt prev_hash of event at index 5
        tampered = [StateEvent(
            tick=e.tick,
            timestamp=e.timestamp,
            event_type=e.event_type,
            source=e.source,
            payload=e.payload,
            prev_hash=e.prev_hash,
            hash=e.hash,
        ) for e in ledger]

        tampered[5] = StateEvent(
            tick=tampered[5].tick,
            timestamp=tampered[5].timestamp,
            event_type=tampered[5].event_type,
            source=tampered[5].source,
            payload=tampered[5].payload,
            prev_hash="CORRUPTED_HASH_000000000000000000000000",
            hash=tampered[5].hash,
        )

        engine = ReplayEngine()
        result = engine.replay(tampered)
        # Divergence must be detected
        assert result.divergence_tick is not None, "Tamper not detected"


class TestReplayFromCheckpoint:
    """Verify partial replay from a specific hash."""

    def test_replay_from_midpoint(self):
        """Replay from a midpoint slices events correctly.

        Note: partial replay from a fresh StateVector will diverge from
        the original chain (genesis hash != checkpoint hash). This is
        expected. We verify: (a) correct event slicing, (b) ticks match
        the remaining events, (c) two identical partial replays converge.
        """
        ledger = _build_ledger_from_trace(CANONICAL_TRACE)
        midpoint_hash = ledger[5].prev_hash  # Start from event 5's prev_hash
        expected_ticks = len(ledger) - 5  # Events from index 5 onward

        engine = ReplayEngine()
        r1 = engine.replay_from_hash(ledger, start_hash=midpoint_hash)
        r2 = engine.replay_from_hash(ledger, start_hash=midpoint_hash)

        # Partial replay processes the correct number of ticks
        assert r1.ticks_replayed == expected_ticks
        # Two partial replays are identical (deterministic)
        assert r1.final_hash == r2.final_hash
        assert r1.ticks_replayed == r2.ticks_replayed

    def test_replay_from_invalid_hash_fails(self):
        """Replay from nonexistent hash returns failure."""
        ledger = _build_ledger_from_trace(CANONICAL_TRACE)
        engine = ReplayEngine()
        result = engine.replay_from_hash(ledger, start_hash="nonexistent_hash_abc")

        assert not result.success
        assert len(result.errors) > 0


class TestReplaySnapshot:
    """Verify snapshot consistency between original and replayed state."""

    def test_snapshot_fields_match(self):
        """Replayed snapshot must contain all expected structural fields."""
        ledger = _build_ledger_from_trace(CANONICAL_TRACE)
        engine = ReplayEngine()
        result = engine.replay(ledger)

        snap = result.final_snapshot
        required_fields = [
            "tick", "entropy", "exergy", "agents_active", "agents_total",
            "tasks_pending", "tasks_completed", "tasks_failed",
            "error_pressure", "throughput", "phase", "hash",
        ]
        for field in required_fields:
            assert field in snap, f"Missing field in snapshot: {field}"

    def test_snapshot_invariants(self):
        """Replayed snapshot respects thermodynamic invariants."""
        ledger = _build_ledger_from_trace(CANONICAL_TRACE)
        engine = ReplayEngine()
        result = engine.replay(ledger)

        snap = result.final_snapshot
        assert snap["tick"] == len(CANONICAL_TRACE)
        assert 0.0 <= snap["entropy"] <= 1.0
        assert abs(snap["exergy"] - (1.0 - snap["entropy"])) < 1e-9, "exergy != 1 - entropy"
        assert snap["tasks_completed"] >= 2  # Two tasks in trace
