# [C5-REAL] Exergy-Maximized
"""CORTEX Runtime — Event Replay Engine.

Three capabilities that convert the runtime from "system" to "substrate":

1. ReplayEngine
   - Takes a ledger (list of StateEvents) and replays them
   - Can replay from any checkpoint (hash-addressed)
   - Produces a new SystemStateVector with identical state
   - Proves determinism: replay(ledger) == original_state

2. StateDiff
   - Compares two SystemStateVector snapshots field-by-field
   - Reports deltas with magnitude and direction
   - Detects hash chain divergence (fork detection)

3. FuzzHarness
   - Generates random event sequences
   - Replays them through a fresh StateVector
   - Checks invariants after every mutation
   - Reports the first invariant violation with full context

Together these close the verification loop:
    Record → Replay → Diff → Fuzz → Prove
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

from cortex.runtime.system_state import (
    StateEvent,
    SystemPhase,
    SystemStateVector,
)

logger = logging.getLogger("cortex.runtime.replay")


# ═══════════════════════════════════════════════════════════════════
# 1. EVENT REPLAY ENGINE
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ReplayResult:
    """Result of a replay operation."""
    success: bool
    ticks_replayed: int
    final_hash: str
    final_snapshot: dict[str, Any]
    hash_match: bool  # True if final hash matches expected
    divergence_tick: int | None = None  # First tick where hashes diverged
    errors: list[str] = field(default_factory=list)


class ReplayEngine:
    """Replays a sequence of causal events through a fresh StateVector.

    Usage:
        engine = ReplayEngine()
        result = engine.replay(ledger_events)
        assert result.hash_match  # Proves determinism

        # Replay from a specific checkpoint
        result = engine.replay_from_hash(ledger_events, start_hash="abc...")
    """

    def replay(
        self,
        events: list[StateEvent],
        expected_final_hash: str | None = None,
    ) -> ReplayResult:
        """Replay all events through a fresh StateVector.

        Args:
            events: Ordered list of StateEvents from the ledger.
            expected_final_hash: If provided, verify the final hash matches.

        Returns:
            ReplayResult with the reconstructed state.
        """
        sv = SystemStateVector()
        errors: list[str] = []
        divergence_tick: int | None = None

        for event in events:
            try:
                replayed = sv.apply(
                    event_type=event.event_type,
                    source=event.source,
                    payload=event.payload,
                )

                # Check hash chain continuity
                if replayed.prev_hash != event.prev_hash and divergence_tick is None:
                    divergence_tick = replayed.tick
                    errors.append(
                        f"Hash chain diverged at tick {replayed.tick}: "
                        f"expected prev_hash={event.prev_hash[:16]}... "
                        f"got={replayed.prev_hash[:16]}..."
                    )

            except Exception as exc:
                errors.append(f"Tick {event.tick}: {type(exc).__name__}: {exc}")

        final_hash = sv.hash
        hash_match = (
            final_hash == expected_final_hash
            if expected_final_hash
            else divergence_tick is None
        )

        result = ReplayResult(
            success=len(errors) == 0,
            ticks_replayed=sv.tick,
            final_hash=final_hash,
            final_snapshot=sv.snapshot(),
            hash_match=hash_match,
            divergence_tick=divergence_tick,
            errors=errors,
        )

        logger.info(
            "Replay complete: %d ticks, hash_match=%s, errors=%d",
            result.ticks_replayed,
            result.hash_match,
            len(result.errors),
        )
        return result

    def replay_from_hash(
        self,
        events: list[StateEvent],
        start_hash: str,
        expected_final_hash: str | None = None,
    ) -> ReplayResult:
        """Replay events starting from a specific hash checkpoint.

        Skips all events before the one with prev_hash == start_hash.
        """
        # Find the starting index
        start_idx = None
        for i, event in enumerate(events):
            if event.prev_hash == start_hash:
                start_idx = i
                break

        if start_idx is None:
            return ReplayResult(
                success=False,
                ticks_replayed=0,
                final_hash="",
                final_snapshot={},
                hash_match=False,
                errors=[f"Start hash {start_hash[:16]}... not found in ledger"],
            )

        return self.replay(events[start_idx:], expected_final_hash)

    def verify_determinism(
        self, events: list[StateEvent], runs: int = 3
    ) -> bool:
        """Replay the same ledger N times and verify all produce identical hashes.

        This proves the runtime is fully deterministic.
        """
        hashes: list[str] = []
        for i in range(runs):
            result = self.replay(events)
            hashes.append(result.final_hash)
            logger.debug("Determinism run %d: hash=%s...", i + 1, result.final_hash[:16])

        is_deterministic = len(set(hashes)) == 1
        if not is_deterministic:
            logger.error(
                "DETERMINISM VIOLATION: %d unique hashes across %d runs",
                len(set(hashes)),
                runs,
            )
        return is_deterministic


# ═══════════════════════════════════════════════════════════════════
# 2. STATE DIFF
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FieldDelta:
    """A single field difference between two state snapshots."""
    field: str
    value_a: Any
    value_b: Any
    delta: Any = None  # Numeric difference if applicable

    @property
    def changed(self) -> bool:
        return self.value_a != self.value_b


@dataclass
class StateDiffResult:
    """Result of comparing two state snapshots."""
    identical: bool
    deltas: list[FieldDelta]
    hash_a: str
    hash_b: str
    hash_diverged: bool

    def summary(self) -> str:
        """Human-readable diff summary."""
        if self.identical:
            return "States are identical."
        lines = [f"States diverged ({len(self.deltas)} fields changed):"]
        for d in self.deltas:
            if d.delta is not None:
                lines.append(f"  {d.field}: {d.value_a} → {d.value_b} (Δ{d.delta:+})")
            else:
                lines.append(f"  {d.field}: {d.value_a} → {d.value_b}")
        if self.hash_diverged:
            lines.append(f"  ⚠ HASH CHAIN DIVERGED: {self.hash_a[:16]}... ≠ {self.hash_b[:16]}...")
        return "\n".join(lines)


class StateDiff:
    """Compares two SystemStateVector snapshots."""

    NUMERIC_FIELDS = {
        "tick", "entropy", "exergy", "agents_active", "agents_total",
        "tasks_pending", "tasks_completed", "tasks_failed",
        "error_pressure", "throughput",
    }

    @classmethod
    def diff(
        cls,
        snapshot_a: dict[str, Any],
        snapshot_b: dict[str, Any],
    ) -> StateDiffResult:
        """Compare two state snapshots field by field.

        Args:
            snapshot_a: First snapshot (e.g., from run A).
            snapshot_b: Second snapshot (e.g., from run B).

        Returns:
            StateDiffResult with all field deltas.
        """
        deltas: list[FieldDelta] = []

        all_fields = set(snapshot_a.keys()) | set(snapshot_b.keys())
        for fld in sorted(all_fields):
            val_a = snapshot_a.get(fld)
            val_b = snapshot_b.get(fld)
            if val_a != val_b:
                delta = None
                if fld in cls.NUMERIC_FIELDS and isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                    delta = val_b - val_a
                deltas.append(FieldDelta(
                    field=fld,
                    value_a=val_a,
                    value_b=val_b,
                    delta=delta,
                ))

        hash_a = snapshot_a.get("hash", "")
        hash_b = snapshot_b.get("hash", "")

        return StateDiffResult(
            identical=len(deltas) == 0,
            deltas=deltas,
            hash_a=hash_a,
            hash_b=hash_b,
            hash_diverged=hash_a != hash_b,
        )

    @classmethod
    def diff_vectors(
        cls,
        sv_a: SystemStateVector,
        sv_b: SystemStateVector,
    ) -> StateDiffResult:
        """Compare two live SystemStateVector instances."""
        return cls.diff(sv_a.snapshot(), sv_b.snapshot())


# ═══════════════════════════════════════════════════════════════════
# 3. DETERMINISTIC FUZZ HARNESS
# ═══════════════════════════════════════════════════════════════════

@dataclass
class InvariantViolation:
    """A detected invariant violation during fuzzing."""
    tick: int
    invariant: str
    details: str
    snapshot: dict[str, Any]
    event_type: str
    event_source: str


@dataclass
class FuzzResult:
    """Result of a fuzz run."""
    events_generated: int
    events_replayed: int
    violations: list[InvariantViolation]
    final_snapshot: dict[str, Any]
    seed: int

    @property
    def clean(self) -> bool:
        return len(self.violations) == 0


class FuzzHarness:
    """Deterministic fuzz testing for the SystemStateVector.

    Generates random (but reproducible) event sequences,
    replays them through a fresh StateVector, and checks
    invariants after every mutation.

    Usage:
        harness = FuzzHarness(seed=42)
        result = harness.run(n_events=1000)
        assert result.clean

        # Reproduce a failure
        result2 = harness.run(n_events=1000)  # Same seed → same result
    """

    # Event types the fuzzer can generate
    EVENT_POOL = [
        "agent.started",
        "agent.stopped",
        "agent.registered",
        "task.submitted",
        "task.completed",
        "task.failed",
        "system.error",
        "system.recovery",
        "unknown.event",  # Tests generic handler
    ]

    SOURCE_POOL = [
        "fuzzer",
        "agent-alpha",
        "agent-beta",
        "agent-gamma",
        "system",
    ]

    def __init__(self, seed: int | None = None) -> None:
        self.seed = seed if seed is not None else int(time.time() * 1000) % (2**31)
        self._rng = random.Random(self.seed)

    def run(self, n_events: int = 500) -> FuzzResult:
        """Execute a fuzz run with N random events.

        After each event, all invariants are checked.
        First violation stops the run and is returned with full context.
        """
        # Reset RNG for reproducibility
        self._rng = random.Random(self.seed)

        sv = SystemStateVector()
        violations: list[InvariantViolation] = []
        replayed = 0

        for _ in range(n_events):
            event_type = self._rng.choice(self.EVENT_POOL)
            source = self._rng.choice(self.SOURCE_POOL)

            try:
                sv.apply(event_type, source)
                replayed += 1
            except Exception as exc:
                violations.append(InvariantViolation(
                    tick=sv.tick,
                    invariant="apply_exception",
                    details=f"{type(exc).__name__}: {exc}",
                    snapshot=sv.snapshot(),
                    event_type=event_type,
                    event_source=source,
                ))
                continue

            # Check all invariants
            v = self._check_invariants(sv, event_type, source)
            if v:
                violations.append(v)
                # Don't break — collect all violations for the full picture

        result = FuzzResult(
            events_generated=n_events,
            events_replayed=replayed,
            violations=violations,
            final_snapshot=sv.snapshot(),
            seed=self.seed,
        )

        if violations:
            logger.warning(
                "Fuzz run (seed=%d): %d violations in %d events",
                self.seed, len(violations), n_events,
            )
        else:
            logger.info(
                "Fuzz run (seed=%d): CLEAN — %d events, final entropy=%.3f",
                self.seed, n_events, sv.entropy,
            )
        return result

    def _check_invariants(
        self,
        sv: SystemStateVector,
        event_type: str,
        source: str,
    ) -> InvariantViolation | None:
        """Check all system invariants. Returns violation or None."""
        snap = sv.snapshot()

        # Check bounds and basic constraints
        checks = [
            (abs(snap["entropy"] + snap["exergy"] - 1.0) > 1e-10, "exergy_conservation", f"entropy={snap['entropy']} + exergy={snap['exergy']} != 1.0"),
            (not (0.0 <= snap["entropy"] <= 1.0), "entropy_domain", f"entropy={snap['entropy']} outside [0, 1]"),
            (not (0.0 <= snap["error_pressure"] <= 1.0), "error_pressure_domain", f"error_pressure={snap['error_pressure']} outside [0, 1]"),
            (snap["tick"] < 1, "monotonic_tick", f"tick={snap['tick']} after event"),
            (not snap["hash"], "hash_present", "Empty hash after event"),
        ]
        for cond, inv, details in checks:
            if cond:
                return InvariantViolation(
                    tick=snap["tick"], invariant=inv, details=details,
                    snapshot=snap, event_type=event_type, event_source=source
                )

        # Check non-negative counters
        for counter in ("agents_active", "agents_total", "tasks_pending", "tasks_completed", "tasks_failed"):
            if snap[counter] < 0:
                return InvariantViolation(
                    tick=snap["tick"], invariant=f"non_negative_{counter}", details=f"{counter}={snap[counter]} < 0",
                    snapshot=snap, event_type=event_type, event_source=source
                )

        # Check system phase validity
        try:
            SystemPhase(snap["phase"])
        except ValueError:
            return InvariantViolation(
                tick=snap["tick"], invariant="valid_phase", details=f"Invalid phase: {snap['phase']}",
                snapshot=snap, event_type=event_type, event_source=source
            )

        return None  # All invariants hold
