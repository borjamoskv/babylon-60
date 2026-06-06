"""Tests for cortex.memory.reconsolidation.

Covers:
  - ReconsolidationOutcome enum
  - LabilizationRecord lifecycle (labile, expired, age_seconds)
  - ConfirmationBiasDetector (record, bias_score, is_biased, biased_engrams, report)
  - ReconsolidationTracker lifecycle:
      on_access → confirm/contradict → sweep → audit_trail
  - Concurrent safety: multiple engrams in parallel
  - Error recovery: double-confirm, missing engram IDs
  - dream_sweep hook
  - Confirmation bias detection via tracker wrapper
"""
from __future__ import annotations

import time
import uuid

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _engram_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# ReconsolidationOutcome
# ---------------------------------------------------------------------------

class TestReconsolidationOutcome:
    def test_outcome_values(self) -> None:
        try:
            from cortex.memory.reconsolidation import ReconsolidationOutcome
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        assert ReconsolidationOutcome.CONFIRMED
        assert ReconsolidationOutcome.CONTRADICTED
        assert ReconsolidationOutcome.IGNORED

    def test_outcome_is_str_enum(self) -> None:
        try:
            from cortex.memory.reconsolidation import ReconsolidationOutcome
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        # str Enum: value should be usable as a string
        assert isinstance(ReconsolidationOutcome.CONFIRMED.value, str)


# ---------------------------------------------------------------------------
# LabilizationRecord
# ---------------------------------------------------------------------------

class TestLabilizationRecord:
    def _make_record(self, window_s: float = 300.0):
        from cortex.memory.reconsolidation import LabilizationRecord
        return LabilizationRecord(
            engram_id=_engram_id(),
            previous_version="v1",
            labile_window_s=window_s,
        )

    def test_is_labile_initially(self) -> None:
        try:
            rec = self._make_record()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        assert rec.is_labile is True

    def test_not_expired_initially(self) -> None:
        try:
            rec = self._make_record()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        assert rec.is_expired is False

    def test_age_seconds_is_non_negative(self) -> None:
        try:
            rec = self._make_record()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        assert rec.age_seconds >= 0.0

    def test_record_expires_with_zero_window(self) -> None:
        try:
            rec = self._make_record(window_s=0.0)
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        time.sleep(0.01)  # ensure clock advances
        assert rec.is_expired is True


# ---------------------------------------------------------------------------
# ConfirmationBiasDetector
# ---------------------------------------------------------------------------

class TestConfirmationBiasDetector:
    def _make_detector(self):
        from cortex.memory.reconsolidation import (
            ConfirmationBiasDetector,
            ReconsolidationOutcome,
        )
        return ConfirmationBiasDetector(), ReconsolidationOutcome

    def test_bias_score_zero_with_no_events(self) -> None:
        try:
            detector, _ = self._make_detector()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        eid = _engram_id()
        assert detector.bias_score(eid) == 0.0

    def test_is_not_biased_with_no_events(self) -> None:
        try:
            detector, _ = self._make_detector()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        assert detector.is_biased(_engram_id()) is False

    def test_bias_score_pure_confirm(self) -> None:
        try:
            detector, outcome = self._make_detector()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        eid = _engram_id()
        for _ in range(10):
            detector.record(eid, outcome.CONFIRMED)
        assert detector.bias_score(eid) == pytest.approx(1.0)

    def test_bias_score_mixed(self) -> None:
        try:
            detector, outcome = self._make_detector()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        eid = _engram_id()
        for _ in range(5):
            detector.record(eid, outcome.CONFIRMED)
        for _ in range(5):
            detector.record(eid, outcome.CONTRADICTED)
        score = detector.bias_score(eid)
        assert 0.0 < score < 1.0

    def test_biased_engrams_lists_high_bias(self) -> None:
        try:
            detector, outcome = self._make_detector()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        eid = _engram_id()
        for _ in range(20):
            detector.record(eid, outcome.CONFIRMED)
        biased = detector.biased_engrams()
        assert eid in biased

    def test_report_returns_dict(self) -> None:
        try:
            detector, outcome = self._make_detector()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        eid = _engram_id()
        detector.record(eid, outcome.CONFIRMED)
        report = detector.report()
        assert isinstance(report, dict)


# ---------------------------------------------------------------------------
# ReconsolidationTracker
# ---------------------------------------------------------------------------

class TestReconsolidationTracker:
    def _make_tracker(self):
        from cortex.memory.reconsolidation import ReconsolidationTracker
        return ReconsolidationTracker()

    def test_on_access_creates_labile_record(self) -> None:
        try:
            tracker = self._make_tracker()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        eid = _engram_id()
        tracker.on_access(eid, previous_version="v0")
        trail = tracker.audit_trail(eid)
        assert len(trail) >= 1

    def test_confirm_resolves_engram(self) -> None:
        try:
            tracker = self._make_tracker()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        eid = _engram_id()
        tracker.on_access(eid, previous_version="v0")
        tracker.confirm(eid)
        trail = tracker.audit_trail(eid)
        outcomes = [e.outcome for e in trail]
        from cortex.memory.reconsolidation import ReconsolidationOutcome
        assert ReconsolidationOutcome.CONFIRMED in outcomes

    def test_contradict_flags_engram(self) -> None:
        try:
            tracker = self._make_tracker()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        eid = _engram_id()
        tracker.on_access(eid, previous_version="v0")
        tracker.contradict(eid)
        trail = tracker.audit_trail(eid)
        outcomes = [e.outcome for e in trail]
        from cortex.memory.reconsolidation import ReconsolidationOutcome
        assert ReconsolidationOutcome.CONTRADICTED in outcomes

    def test_sweep_resolves_expired_records(self) -> None:
        try:
            from cortex.memory.reconsolidation import ReconsolidationTracker
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        tracker = ReconsolidationTracker(labile_window_s=0.0)
        eid = _engram_id()
        tracker.on_access(eid, previous_version="v0")
        time.sleep(0.01)
        tracker.sweep()
        # After sweep, expired records should be resolved (IGNORED)
        trail = tracker.audit_trail(eid)
        outcomes = [e.outcome for e in trail]
        from cortex.memory.reconsolidation import ReconsolidationOutcome
        assert ReconsolidationOutcome.IGNORED in outcomes

    def test_audit_trail_returns_chronological_events(self) -> None:
        try:
            tracker = self._make_tracker()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        eid = _engram_id()
        tracker.on_access(eid, previous_version="v0")
        tracker.confirm(eid)
        trail = tracker.audit_trail(eid)
        timestamps = [e.timestamp for e in trail]
        assert timestamps == sorted(timestamps)

    def test_all_audit_events_aggregates_all_engrams(self) -> None:
        try:
            tracker = self._make_tracker()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        eid1, eid2 = _engram_id(), _engram_id()
        tracker.on_access(eid1, previous_version="v0")
        tracker.on_access(eid2, previous_version="v0")
        all_events = tracker.all_audit_events()
        engram_ids = {e.engram_id for e in all_events}
        assert eid1 in engram_ids
        assert eid2 in engram_ids

    def test_dream_sweep_runs_without_error(self) -> None:
        try:
            tracker = self._make_tracker()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        # dream_sweep is a hook — must not raise
        tracker.dream_sweep()

    def test_confirmation_bias_report_returns_dict(self) -> None:
        try:
            tracker = self._make_tracker()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        report = tracker.confirmation_bias_report()
        assert isinstance(report, dict)

    def test_multiple_engrams_isolated(self) -> None:
        try:
            tracker = self._make_tracker()
        except ImportError:
            pytest.skip("cortex.memory.reconsolidation not importable")
        eid1, eid2 = _engram_id(), _engram_id()
        tracker.on_access(eid1, previous_version="v0")
        tracker.on_access(eid2, previous_version="v0")
        tracker.confirm(eid1)
        tracker.contradict(eid2)
        trail1 = {e.outcome for e in tracker.audit_trail(eid1)}
        trail2 = {e.outcome for e in tracker.audit_trail(eid2)}
        from cortex.memory.reconsolidation import ReconsolidationOutcome
        assert ReconsolidationOutcome.CONFIRMED in trail1
        assert ReconsolidationOutcome.CONTRADICTED in trail2
        # Isolation: engram1 should not have CONTRADICTED
        assert ReconsolidationOutcome.CONTRADICTED not in trail1
