"""Regression tests for the sovereign guard runtime wrappers."""

from __future__ import annotations

import sys

import pytest

from cortex.extensions.security.guard_runtime import (
    AnomalyGuardWrapper,
    HoneypotGuardWrapper,
    InjectionGuardWrapper,
    enforce_guard_pipeline,
)


def _missing_module(monkeypatch: pytest.MonkeyPatch, module_name: str) -> None:
    monkeypatch.setitem(sys.modules, module_name, None)


def test_missing_injection_guard_blocks_direct_evaluation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _missing_module(monkeypatch, "cortex.extensions.security.injection_guard")

    outcome = InjectionGuardWrapper().evaluate(
        {"content": "persist me", "project": "p", "source": "agent:test"}
    )

    assert outcome.allowed is False
    assert outcome.severity == "critical"
    assert outcome.code == "injection.guard_missing"


def test_missing_honeypot_guard_blocks_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _missing_module(monkeypatch, "cortex.extensions.security.honeypot")

    with pytest.raises(RuntimeError, match="Mandatory guard honeypot_guard"):
        enforce_guard_pipeline(
            [HoneypotGuardWrapper()],
            {"content": "persist me", "project": "p", "source": "agent:test"},
        )


def test_missing_optional_anomaly_guard_still_allows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _missing_module(monkeypatch, "cortex.extensions.security.anomaly_detector")

    outcome = AnomalyGuardWrapper().evaluate(
        {"content": "persist me", "project": "p", "source": "agent:test"}
    )

    assert outcome.allowed is True
    assert outcome.reason == "AnomalyDetector missing, skipping"
