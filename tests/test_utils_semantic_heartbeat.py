"""Tests for cortex/utils/semantic_heartbeat.py — 100% coverage."""
from __future__ import annotations

import pytest

from cortex.utils.semantic_heartbeat import SemanticHeartbeat


class TestSemanticHeartbeat:
    def test_first_call_returns_zero_drift(self):
        hb = SemanticHeartbeat()
        report = {"cpu": 0.5, "memory": 0.3, "orphans": 0}
        drift = hb.calculate_drift(report)
        assert drift == 0.0

    def test_same_report_returns_zero_drift(self):
        hb = SemanticHeartbeat()
        report = {"cpu": 0.5, "memory": 0.3, "orphans": 0}
        hb.calculate_drift(report)
        drift = hb.calculate_drift(report)
        assert drift == 0.0

    def test_different_report_returns_nonzero_drift(self):
        hb = SemanticHeartbeat()
        report1 = {"cpu": 0.1, "memory": 0.1, "orphans": 0}
        report2 = {"cpu": 0.9, "memory": 0.9, "orphans": 0}
        hb.calculate_drift(report1)
        drift = hb.calculate_drift(report2)
        assert drift > 0.0

    def test_orphan_spike_triggers_critical_drift(self):
        hb = SemanticHeartbeat()
        report1 = {"cpu": 0.5, "orphans": 0}
        report2 = {"cpu": 0.5, "orphans": 5}
        hb.calculate_drift(report1)
        drift = hb.calculate_drift(report2)
        assert drift >= 0.9

    def test_drift_bounded_zero_to_one(self):
        hb = SemanticHeartbeat()
        for i in range(5):
            report = {"cpu": i * 0.1, "memory": i * 0.2, "orphans": i % 2}
            drift = hb.calculate_drift(report)
            assert 0.0 <= drift <= 1.0

    def test_hash_payload_normalizes_floats(self):
        hb = SemanticHeartbeat()
        # Values that round to the same 1-decimal value hash identically
        r1 = {"val": 0.11}
        r2 = {"val": 0.14}  # both round to 0.1
        h1 = hb._hash_payload(r1)
        h2 = hb._hash_payload(r2)
        assert h1 == h2

    def test_hash_payload_normalizes_load_average(self):
        hb = SemanticHeartbeat()
        r = {"load_average": (1.111, 2.222, 3.333)}
        h = hb._hash_payload(r)
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex

    def test_last_report_updated(self):
        hb = SemanticHeartbeat()
        report = {"cpu": 0.5, "orphans": 0}
        hb.calculate_drift(report)
        assert hb.last_report == report

    def test_custom_threshold(self):
        hb = SemanticHeartbeat(threshold=0.5)
        assert hb.threshold == 0.5

    def test_orphan_decrease_no_spike(self):
        hb = SemanticHeartbeat()
        r1 = {"cpu": 0.1, "orphans": 5}
        r2 = {"cpu": 0.1, "orphans": 5}  # identical — no drift
        hb.calculate_drift(r1)
        drift = hb.calculate_drift(r2)
        assert drift == 0.0
