from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cortex.mac_maestro.access import MacCapabilityStatus, MaestroAccessProfile
from cortex.mac_maestro.executor import MaestroExecutor
from cortex.mac_maestro.intent import MacAction
from sdks.mac_maestro.models import UIAction


def _status(name: str, granted: bool | None) -> MacCapabilityStatus:
    if granted is True:
        state = "granted"
    elif granted is False:
        state = "denied"
    else:
        state = "unknown"
    return MacCapabilityStatus(
        name=name,
        state=state,
        available=True,
        granted=granted,
        prompt_supported=True,
    )


def _profile(
    *, automation: bool | None = True, accessibility: bool | None = True
) -> MaestroAccessProfile:
    return MaestroAccessProfile(
        accessibility=_status("accessibility", accessibility),
        automation=_status("automation", automation),
        axui_element=_status("axui_element", accessibility),
        screen_recording=_status("screen_recording", True),
        input_monitoring=_status("input_monitoring", True),
    )


def test_executor_blocks_when_automation_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = MaestroExecutor(ledger_writer=MagicMock())
    monkeypatch.setattr(
        "cortex.mac_maestro.executor.collect_access_profile",
        lambda **kwargs: _profile(automation=False),
    )

    with pytest.raises(PermissionError, match="automation"):
        executor._ensure_action_access(
            MacAction(action="activate", app="Finder"),
            UIAction(name="activate", vector="A"),
        )


def test_executor_allows_ax_action_when_permissions_are_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executor = MaestroExecutor(ledger_writer=MagicMock())
    monkeypatch.setattr(
        "cortex.mac_maestro.executor.collect_access_profile",
        lambda **kwargs: _profile(accessibility=True),
    )

    executor._ensure_action_access(
        MacAction(action="click", app="Finder"),
        UIAction(name="click", vector="B"),
    )
