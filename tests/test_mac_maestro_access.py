from __future__ import annotations

import sys
import types

import pytest

from cortex.mac_maestro import access
from cortex.mac_maestro.access import MacCapabilityStatus, MaestroAccessProfile


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


def test_probe_accessibility_access_is_unsupported_off_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(access, "_is_macos", lambda: False)

    status = access.probe_accessibility_access()

    assert status.state == "unsupported"
    assert status.ready is False


def test_probe_accessibility_access_uses_prompt_option(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(access, "_is_macos", lambda: True)
    fake_application_services = types.SimpleNamespace(
        AXIsProcessTrusted=lambda: False,
        AXIsProcessTrustedWithOptions=lambda options: options == {"AXPrompt": True},
        kAXTrustedCheckOptionPrompt="AXPrompt",
    )
    monkeypatch.setitem(sys.modules, "ApplicationServices", fake_application_services)

    status = access.probe_accessibility_access(prompt=True)

    assert status.ready is True
    assert status.prompted is True
    assert status.settings_path == access.ACCESSIBILITY_SETTINGS


def test_probe_automation_access_is_unknown_until_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(access, "_is_macos", lambda: True)
    monkeypatch.setattr(access.shutil, "which", lambda _: "/usr/bin/osascript")

    status = access.probe_automation_access("Finder", request=False)

    assert status.state == "unknown"
    assert status.target == "Finder"
    assert status.prompt_supported is True


def test_probe_automation_access_detects_denial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(access, "_is_macos", lambda: True)
    monkeypatch.setattr(access.shutil, "which", lambda _: "/usr/bin/osascript")
    denied = types.SimpleNamespace(
        returncode=1,
        stdout="",
        stderr="Not authorized to send Apple events to Finder. (-1743)",
    )
    monkeypatch.setattr(access.subprocess, "run", lambda *args, **kwargs: denied)

    status = access.probe_automation_access("Finder", request=True)

    assert status.state == "denied"
    assert status.target == "Finder"
    assert status.prompted is True


def test_probe_screen_recording_access_requests_when_prompted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(access, "_is_macos", lambda: True)
    fake_quartz = types.SimpleNamespace(
        CGPreflightScreenCaptureAccess=lambda: False,
        CGRequestScreenCaptureAccess=lambda: True,
    )
    monkeypatch.setitem(sys.modules, "Quartz", fake_quartz)

    status = access.probe_screen_recording_access(prompt=True)

    assert status.ready is True
    assert status.prompted is True
    assert status.settings_path == access.SCREEN_RECORDING_SETTINGS


def test_access_profile_reports_missing_gui_scripting_capabilities() -> None:
    profile = MaestroAccessProfile(
        accessibility=_status("accessibility", False),
        automation=_status("automation", None),
        axui_element=_status("axui_element", True),
        screen_recording=_status("screen_recording", True),
        input_monitoring=_status("input_monitoring", True),
    )

    missing = profile.missing_for_surface("gui_scripting")

    assert [status.name for status in missing] == ["accessibility", "automation"]
