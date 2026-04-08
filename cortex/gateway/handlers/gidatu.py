"""Gidatu UI/Desktop Orchestration Handler.
Ω₃ (Byzantine Default): Enforces SafeZones and strict app-scoping.
"""

import logging
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from cortex.core.paths import resolve_skill_scripts_dir

if TYPE_CHECKING:
    from cortex.gateway import GatewayRequest

logger = logging.getLogger("cortex.gateway.gidatu")


class GidatuHandler:
    """Handles UI orchestration requests using the Gidatu skill."""

    def __init__(self, skill_name: str = "Gidatu", skills_root: Optional[Path] = None) -> None:
        if skills_root is None:
            self._skill_path = resolve_skill_scripts_dir(skill_name)
        else:
            self._skill_path = skills_root / skill_name / "scripts"
        self._runtime: dict[str, Any] | None = None

    def _ensure_path(self) -> None:
        if self._skill_path.is_dir() and str(self._skill_path) not in sys.path:
            sys.path.insert(0, str(self._skill_path))

    def _load_runtime(self) -> dict[str, Any]:
        if self._runtime is not None:
            return self._runtime

        self._ensure_path()
        try:
            from ghost_chain import Ghost  # type: ignore[import-not-found, reportMissingImports]
            from ghost_platform import (
                platform_info,  # type: ignore[import-not-found, reportMissingImports]
            )
            from ghost_vlm import (
                find_text_on_screen,  # type: ignore[import-not-found, reportMissingImports]
            )
        except ImportError as e:
            raise ImportError(f"Gidatu runtime imports not available at {self._skill_path}") from e

        try:
            from ghost_guard import SafeZone  # type: ignore[import-not-found, reportMissingImports]
        except ImportError:
            SafeZone = None

        try:
            from ghost_resilience import (
                wait_until,  # type: ignore[import-not-found, reportMissingImports]
            )
        except ImportError:
            wait_until = None

        self._runtime = {
            "Ghost": Ghost,
            "SafeZone": SafeZone,
            "find_text_on_screen": find_text_on_screen,
            "platform_info": platform_info,
            "wait_until": wait_until,
        }
        return self._runtime

    async def handle(self, req: "GatewayRequest") -> dict[str, Any]:
        """Process a Gidatu action request."""
        if not self._skill_path.is_dir():
            raise ImportError(f"Gidatu skill scripts not found at {self._skill_path}")

        runtime = self._load_runtime()

        action = req.payload.get("action", "status")
        params = req.payload.get("params", {})
        timeout = float(req.payload.get("timeout", 5.0))
        app = req.payload.get("app")

        # logic for actions - Wrap in to_thread for non-blocking IO
        import asyncio

        return await asyncio.to_thread(self._sync_handle, runtime, action, params, timeout, app)

    def _sync_handle(
        self,
        runtime: dict[str, Any],
        action: str,
        params: dict,
        timeout: float,
        app: Optional[str],
    ) -> dict[str, Any]:
        Ghost = runtime["Ghost"]
        SafeZone = runtime["SafeZone"]
        platform_info = runtime["platform_info"]
        find_text_on_screen = runtime["find_text_on_screen"]

        with Ghost(app=app) as g:
            # Native SafeZone enforcement (Ω₃)
            if "safe_zone" in params:
                if SafeZone is None:
                    raise ImportError(f"Gidatu safe-zone runtime not available at {self._skill_path}")
                sz = params["safe_zone"]
                g.guard_zone(SafeZone(sz["x"], sz["y"], sz["w"], sz["h"]))

            if action == "click":
                return self._do_click(g, params)

            if action == "click_text":
                return self._do_click_text(runtime, g, params, timeout)

            if action == "type":
                g.type(params["text"])
                return {"action": "type", "success": True}

            if action == "hotkey":
                g.hotkey(*params["keys"])
                return {"action": "hotkey", "keys": params["keys"]}

            if action == "screenshot":
                path = params.get("path", f"/tmp/shot_{int(time.time())}.png")
                g.screenshot(path)
                return {"action": "screenshot", "path": path}

            if action == "vlm":
                text = params.get("text")
                match = find_text_on_screen(text) if text else None
                return {"action": "vlm", "found": bool(match), "match": match}

            if action == "status":
                return {"status": "ready", "platform": platform_info()}

            raise ValueError(f"Unknown Gidatu action: {action}")

    def _do_click(self, g: Any, params: dict[str, Any]) -> dict[str, Any]:
        x, y = params.get("x"), params.get("y")
        if x is None or y is None:
            raise ValueError("params.x and params.y are required for click")
        g.click(x, y)
        return {"action": "click", "coords": [x, y]}

    def _do_click_text(
        self, runtime: dict[str, Any], g: Any, params: dict[str, Any], timeout: float
    ) -> dict[str, Any]:
        wait_until = runtime["wait_until"]
        find_text_on_screen = runtime["find_text_on_screen"]
        if wait_until is None:
            raise ImportError(f"Gidatu click_text runtime not available at {self._skill_path}")
        text = params.get("text")
        if not text:
            raise ValueError("params.text is required for click_text")
        found = wait_until(lambda: find_text_on_screen(text), timeout=timeout)
        if not found:
            raise RuntimeError(f"Text '{text}' not found on screen")
        g.click(found["x"], found["y"])
        return {"action": "click_text", "text": text, "coords": [found["x"], found["y"]]}
