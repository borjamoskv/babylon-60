from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Literal

AccessState = Literal["granted", "denied", "unknown", "unavailable", "unsupported"]

ACCESSIBILITY_SETTINGS = "System Settings -> Privacy & Security -> Accessibility"
AUTOMATION_SETTINGS = "System Settings -> Privacy & Security -> Automation"
SCREEN_RECORDING_SETTINGS = "System Settings -> Privacy & Security -> Screen & System Audio Recording"
INPUT_MONITORING_SETTINGS = "System Settings -> Privacy & Security -> Input Monitoring"


@dataclass(frozen=True)
class MacCapabilityStatus:
    name: str
    state: AccessState
    available: bool
    granted: bool | None
    prompt_supported: bool
    prompted: bool = False
    target: str | None = None
    api: str | None = None
    settings_path: str | None = None
    detail: str | None = None

    @property
    def ready(self) -> bool:
        return self.granted is True


@dataclass(frozen=True)
class MaestroAccessProfile:
    accessibility: MacCapabilityStatus
    automation: MacCapabilityStatus
    axui_element: MacCapabilityStatus
    screen_recording: MacCapabilityStatus
    input_monitoring: MacCapabilityStatus

    def missing_for_surface(self, surface: str) -> list[MacCapabilityStatus]:
        requirements = {
            "accessibility": (self.accessibility,),
            "automation": (self.automation,),
            "gui_scripting": (self.accessibility, self.automation),
            "axui_element": (self.accessibility, self.axui_element),
            "screen_capture": (self.screen_recording,),
            "input_observation": (self.input_monitoring,),
            "synthetic_input": (self.accessibility,),
        }
        if surface not in requirements:
            raise ValueError(f"Unknown surface '{surface}'.")
        return [status for status in requirements[surface] if not status.ready]


def _is_macos() -> bool:
    return sys.platform == "darwin"


def _unsupported_status(
    name: str,
    *,
    settings_path: str | None,
    api: str | None,
    detail: str,
) -> MacCapabilityStatus:
    return MacCapabilityStatus(
        name=name,
        state="unsupported",
        available=False,
        granted=None,
        prompt_supported=False,
        settings_path=settings_path,
        api=api,
        detail=detail,
    )


def _unavailable_status(
    name: str,
    *,
    settings_path: str | None,
    api: str | None,
    detail: str,
) -> MacCapabilityStatus:
    return MacCapabilityStatus(
        name=name,
        state="unavailable",
        available=False,
        granted=None,
        prompt_supported=False,
        settings_path=settings_path,
        api=api,
        detail=detail,
    )


def _state_status(
    name: str,
    *,
    granted: bool | None,
    prompt_supported: bool,
    settings_path: str | None,
    api: str | None,
    detail: str,
    prompted: bool = False,
    target: str | None = None,
) -> MacCapabilityStatus:
    if granted is True:
        state: AccessState = "granted"
    elif granted is False:
        state = "denied"
    else:
        state = "unknown"
    return MacCapabilityStatus(
        name=name,
        state=state,
        available=True,
        granted=granted,
        prompt_supported=prompt_supported,
        prompted=prompted,
        target=target,
        settings_path=settings_path,
        api=api,
        detail=detail,
    )


def probe_accessibility_access(prompt: bool = False) -> MacCapabilityStatus:
    if not _is_macos():
        return _unsupported_status(
            "accessibility",
            settings_path=ACCESSIBILITY_SETTINGS,
            api="AXIsProcessTrusted",
            detail="Accessibility control is only available on macOS.",
        )

    try:
        import ApplicationServices as app_services  # type: ignore[import-not-found, reportMissingImports]
    except ImportError:
        return _unavailable_status(
            "accessibility",
            settings_path=ACCESSIBILITY_SETTINGS,
            api="AXIsProcessTrusted",
            detail="ApplicationServices accessibility bindings are unavailable.",
        )

    ax_is_process_trusted = getattr(app_services, "AXIsProcessTrusted", None)
    ax_is_process_trusted_with_options = getattr(
        app_services,
        "AXIsProcessTrustedWithOptions",
        None,
    )
    ax_prompt_key = getattr(app_services, "kAXTrustedCheckOptionPrompt", None)
    if ax_is_process_trusted is None or ax_is_process_trusted_with_options is None:
        return _unavailable_status(
            "accessibility",
            settings_path=ACCESSIBILITY_SETTINGS,
            api="AXIsProcessTrusted",
            detail="ApplicationServices accessibility symbols are unavailable.",
        )

    if prompt:
        granted = bool(ax_is_process_trusted_with_options({ax_prompt_key: True}))
    else:
        granted = bool(ax_is_process_trusted())

    return _state_status(
        "accessibility",
        granted=granted,
        prompt_supported=True,
        prompted=prompt,
        settings_path=ACCESSIBILITY_SETTINGS,
        api="AXIsProcessTrusted",
        detail=(
            "Accessibility allows this process to drive scripts, synthetic input, and UI control."
        ),
    )


def probe_axui_element_access() -> MacCapabilityStatus:
    if not _is_macos():
        return _unsupported_status(
            "axui_element",
            settings_path=ACCESSIBILITY_SETTINGS,
            api="AXUIElement",
            detail="AXUIElement is only available on macOS.",
        )

    try:
        import ApplicationServices as app_services  # type: ignore[import-not-found, reportMissingImports]
    except ImportError:
        return _unavailable_status(
            "axui_element",
            settings_path=ACCESSIBILITY_SETTINGS,
            api="AXUIElement",
            detail="ApplicationServices AXUIElement bindings are unavailable.",
        )

    ax_copy_attribute_value = getattr(app_services, "AXUIElementCopyAttributeValue", None)
    ax_create_application = getattr(app_services, "AXUIElementCreateApplication", None)
    ax_perform_action = getattr(app_services, "AXUIElementPerformAction", None)

    accessibility = probe_accessibility_access(prompt=False)
    granted = accessibility.granted if accessibility.available else None
    return _state_status(
        "axui_element",
        granted=granted,
        prompt_supported=False,
        settings_path=ACCESSIBILITY_SETTINGS,
        api="AXUIElement",
        detail=(
            "AXUIElement can inspect and act on other apps' accessibility trees."
            f" Symbols present: {all([ax_create_application, ax_copy_attribute_value, ax_perform_action])}."
        ),
    )


def probe_automation_access(
    target_app: str = "System Events",
    *,
    request: bool = False,
    timeout: float = 5.0,
) -> MacCapabilityStatus:
    if not _is_macos():
        return _unsupported_status(
            "automation",
            settings_path=AUTOMATION_SETTINGS,
            api="Apple Events / osascript",
            detail="Automation is only available on macOS.",
        )

    if shutil.which("osascript") is None:
        return _unavailable_status(
            "automation",
            settings_path=AUTOMATION_SETTINGS,
            api="Apple Events / osascript",
            detail="osascript is not available in PATH.",
        )

    if not request:
        return _state_status(
            "automation",
            granted=None,
            prompt_supported=True,
            settings_path=AUTOMATION_SETTINGS,
            api="Apple Events / osascript",
            target=target_app,
            detail=(
                "Automation consent is target-specific. Pass request=True to probe or prompt "
                f"for control of '{target_app}'."
            ),
        )

    safe_app = target_app.replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "{safe_app}" to return name'
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    stderr = result.stderr.strip()
    if result.returncode == 0:
        granted = True
        detail = f"Apple Events to '{target_app}' succeeded."
    else:
        lowered = stderr.casefold()
        denied_markers = (
            "-1743",
            "not authorized to send apple events",
            "not permitted to send apple events",
        )
        if any(marker in lowered for marker in denied_markers):
            granted = False
            detail = f"Automation denied for '{target_app}': {stderr or 'Apple Events blocked.'}"
        else:
            granted = None
            detail = (
                f"Automation probe for '{target_app}' did not complete cleanly: "
                f"{stderr or f'osascript rc={result.returncode}'}"
            )

    return _state_status(
        "automation",
        granted=granted,
        prompt_supported=True,
        prompted=True,
        settings_path=AUTOMATION_SETTINGS,
        api="Apple Events / osascript",
        target=target_app,
        detail=detail,
    )


def probe_screen_recording_access(prompt: bool = False) -> MacCapabilityStatus:
    if not _is_macos():
        return _unsupported_status(
            "screen_recording",
            settings_path=SCREEN_RECORDING_SETTINGS,
            api="CGPreflightScreenCaptureAccess",
            detail="Screen recording is only available on macOS.",
        )

    try:
        import Quartz as quartz  # type: ignore[import-not-found, reportMissingImports]
    except ImportError:
        return _unavailable_status(
            "screen_recording",
            settings_path=SCREEN_RECORDING_SETTINGS,
            api="CGPreflightScreenCaptureAccess",
            detail="Quartz screen capture bindings are unavailable.",
        )

    preflight_screen_capture = getattr(quartz, "CGPreflightScreenCaptureAccess", None)
    request_screen_capture = getattr(quartz, "CGRequestScreenCaptureAccess", None)
    if preflight_screen_capture is None or request_screen_capture is None:
        return _unavailable_status(
            "screen_recording",
            settings_path=SCREEN_RECORDING_SETTINGS,
            api="CGPreflightScreenCaptureAccess",
            detail="Quartz screen capture symbols are unavailable.",
        )

    granted = bool(preflight_screen_capture())
    prompted = False
    if prompt and not granted:
        granted = bool(request_screen_capture())
        prompted = True

    return _state_status(
        "screen_recording",
        granted=granted,
        prompt_supported=True,
        prompted=prompted,
        settings_path=SCREEN_RECORDING_SETTINGS,
        api="CGPreflightScreenCaptureAccess",
        detail=(
            "Screen capture permission gates screenshots and, on recent macOS releases, "
            "the Screen & System Audio Recording privacy pane."
        ),
    )


def probe_input_monitoring_access(prompt: bool = False) -> MacCapabilityStatus:
    if not _is_macos():
        return _unsupported_status(
            "input_monitoring",
            settings_path=INPUT_MONITORING_SETTINGS,
            api="CGPreflightListenEventAccess",
            detail="Input monitoring is only available on macOS.",
        )

    try:
        import Quartz as quartz  # type: ignore[import-not-found, reportMissingImports]
    except ImportError:
        return _unavailable_status(
            "input_monitoring",
            settings_path=INPUT_MONITORING_SETTINGS,
            api="CGPreflightListenEventAccess",
            detail="Quartz event-listening bindings are unavailable.",
        )

    preflight_listen_access = getattr(quartz, "CGPreflightListenEventAccess", None)
    request_listen_access = getattr(quartz, "CGRequestListenEventAccess", None)
    if preflight_listen_access is None or request_listen_access is None:
        return _unavailable_status(
            "input_monitoring",
            settings_path=INPUT_MONITORING_SETTINGS,
            api="CGPreflightListenEventAccess",
            detail="Quartz event-listening symbols are unavailable.",
        )

    granted = bool(preflight_listen_access())
    prompted = False
    if prompt and not granted:
        granted = bool(request_listen_access())
        prompted = True

    return _state_status(
        "input_monitoring",
        granted=granted,
        prompt_supported=True,
        prompted=prompted,
        settings_path=INPUT_MONITORING_SETTINGS,
        api="CGPreflightListenEventAccess",
        detail="Input Monitoring is only required for observing keyboard or mouse activity.",
    )


def collect_access_profile(
    *,
    prompt_accessibility: bool = False,
    automation_target: str = "System Events",
    request_automation: bool = False,
    prompt_screen_recording: bool = False,
    prompt_input_monitoring: bool = False,
) -> MaestroAccessProfile:
    return MaestroAccessProfile(
        accessibility=probe_accessibility_access(prompt=prompt_accessibility),
        automation=probe_automation_access(
            automation_target,
            request=request_automation,
        ),
        axui_element=probe_axui_element_access(),
        screen_recording=probe_screen_recording_access(prompt=prompt_screen_recording),
        input_monitoring=probe_input_monitoring_access(prompt=prompt_input_monitoring),
    )
