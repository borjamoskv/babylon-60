#!/usr/bin/env python3
"""Deterministic local stub for the CORTEX FL Studio MCP bridge.

The real integration point is a local process that talks to FL Studio through
its preferred automation layer. This stub keeps a tiny JSON state file so the
MCP tools can be exercised end-to-end before the real bridge exists.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

_DEFAULT_STATE = {
    "project_name": "CORTEX FL Demo",
    "connected": True,
    "playing": False,
    "tempo_bpm": "128",
    "song_position": "1:01:00",
    "channels": ["Kick", "Snare", "Bass", "Pad"],
}


def _state_path() -> Path:
    raw = os.getenv("CORTEX_FL_STUDIO_STATE_FILE", "").strip()
    if raw:
        return Path(raw)
    return Path(tempfile.gettempdir()) / "cortex_fl_studio_stub_state.json"


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return dict(_DEFAULT_STATE)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT_STATE)


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _success(message: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "message": message, "data": data}


def _handle_action(action: str, params: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    if action == "session.status":
        return _success("Bridge connected.", state)

    if action == "transport.status":
        return _success(
            "Transport status loaded.",
            {
                "playing": state["playing"],
                "tempo_bpm": state["tempo_bpm"],
                "song_position": state["song_position"],
            },
        )

    if action == "mixer.channels.list":
        return _success("Channels listed.", {"channels": state["channels"]})

    if action == "transport.play":
        state["playing"] = True
        _save_state(state)
        return _success("FL Studio transport started.", {"playing": True})

    if action == "transport.stop":
        state["playing"] = False
        _save_state(state)
        return _success("FL Studio transport stopped.", {"playing": False})

    if action == "project.tempo.set":
        tempo_bpm = str(params.get("tempo_bpm", "")).strip()
        if not tempo_bpm:
            return {"ok": False, "message": "tempo_bpm is required"}
        state["tempo_bpm"] = tempo_bpm
        _save_state(state)
        return _success(f"FL Studio tempo set to {tempo_bpm} BPM.", {"tempo_bpm": tempo_bpm})

    return {"ok": False, "message": f"Unsupported action: {action}"}


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        sys.stderr.write("Invalid JSON input.\n")
        return 1

    action = str(payload.get("action", "")).strip()
    params = payload.get("params", {})
    if not isinstance(params, dict):
        params = {}

    response = _handle_action(action, params, _load_state())
    sys.stdout.write(json.dumps(response, ensure_ascii=True))
    return 0 if response.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
