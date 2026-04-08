from __future__ import annotations

import asyncio
import base64
import json
import logging
import math
import time
from collections import deque
from collections.abc import Awaitable, Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import websockets
from websockets.exceptions import WebSocketException
from websockets.legacy.client import WebSocketClientProtocol

logger = logging.getLogger("mac-control-omega")


@dataclass(frozen=True)
class CommandTelemetry:
    """Recent kinetic telemetry sample for a CDP command."""

    command: str
    latency_ms: float
    ok: bool


@dataclass
class EventWaiter:
    """Pending waiter for an unsolicited CDP event."""

    method: str
    future: asyncio.Future[dict[str, Any]]
    predicate: Any = None


class MacControlOmega:
    """Sovereign macOS UI Control via raw CDP."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9222,
        timeout: float = 5.0,
        *,
        history_size: int = 64,
        base_delay_s: float = 0.0,
        adaptive_pacing: bool = False,
        max_suggested_delay_s: float = 1.0,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        self.ws_url: str | None = None
        self.ws: WebSocketClientProtocol | None = None
        self.msg_id = 0
        self.base_delay_s = max(0.0, base_delay_s)
        self.adaptive_pacing = adaptive_pacing
        self.max_suggested_delay_s = max(0.0, max_suggested_delay_s)
        self._telemetry: deque[CommandTelemetry] = deque(maxlen=max(1, history_size))
        self._events: deque[dict[str, Any]] = deque(maxlen=256)
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._buffered_responses: dict[int, dict[str, Any]] = {}
        self._event_waiters: list[EventWaiter] = []
        self._reader_task: asyncio.Task[None] | None = None
        self._send_lock = asyncio.Lock()
        self._event_count = 0
        self._event_breakdown: dict[str, int] = {}
        self._last_event_method: str | None = None
        self._lifecycle_state: str | None = None
        self._timeout_count = 0
        self._transport_error_count = 0
        self._cdp_error_count = 0
        self._inflight_count = 0
        self._max_inflight_count = 0
        self._connected_since: float | None = None

    @staticmethod
    def _json_literal(value: str) -> str:
        """Serialize a string as a safe JavaScript literal."""
        return json.dumps(value)

    @classmethod
    def _selector_expression(cls, selector: str, prop: str) -> str:
        selector_literal = cls._json_literal(selector)
        prop_literal = cls._json_literal(prop)
        return (
            "(() => {"
            f"const el = document.querySelector({selector_literal});"
            "if (!el) { return null; }"
            f"return el[{prop_literal}] ?? null;"
            "})()"
        )

    @classmethod
    def _selector_presence_expression(cls, selector: str, *, visible: bool) -> str:
        selector_literal = cls._json_literal(selector)
        if not visible:
            return (
                "(() => {"
                f"return Boolean(document.querySelector({selector_literal}));"
                "})()"
            )
        return (
            "(() => {"
            f"const el = document.querySelector({selector_literal});"
            "if (!el) { return false; }"
            "const rect = el.getBoundingClientRect();"
            "const style = window.getComputedStyle(el);"
            "return rect.width > 0 && rect.height > 0 && style.display !== 'none' && "
            "style.visibility !== 'hidden';"
            "})()"
        )

    @classmethod
    def _text_presence_expression(cls, text: str, selector: str | None = None) -> str:
        text_literal = cls._json_literal(text)
        if selector:
            selector_literal = cls._json_literal(selector)
            scope = (
                f"document.querySelector({selector_literal})?.innerText ?? "
                f"document.querySelector({selector_literal})?.textContent ?? ''"
            )
        else:
            scope = "document.body?.innerText ?? document.body?.textContent ?? ''"
        return (
            "(() => {"
            f"const haystack = {scope};"
            f"return haystack.includes({text_literal});"
            "})()"
        )

    @staticmethod
    def _matches_target(tab: Mapping[str, Any], target_url_substring: str) -> bool:
        if tab.get("type") != "page":
            return False
        if not target_url_substring:
            return True
        needle = target_url_substring.casefold()
        haystacks = (str(tab.get("url", "")), str(tab.get("title", "")))
        return any(needle in value.casefold() for value in haystacks)

    @staticmethod
    def _find_target_tab(
        tabs: Any, target_url_substring: str
    ) -> Mapping[str, Any] | None:
        if not isinstance(tabs, list):
            raise TypeError("CDP /json response must be a list of tabs.")
        for tab in tabs:
            if isinstance(tab, Mapping) and MacControlOmega._matches_target(tab, target_url_substring):
                return tab
        return None

    def _require_ws(self) -> WebSocketClientProtocol:
        if self.ws is None:
            raise RuntimeError("CDP websocket is not connected.")
        return self.ws

    def _ensure_reader_task(self) -> None:
        if self.ws is None:
            return
        if self._reader_task is None or self._reader_task.done():
            self._reader_task = asyncio.create_task(
                self._reader_loop(),
                name="mac-control-omega-reader",
            )

    def _fail_pending(self, exc: BaseException) -> None:
        for future in list(self._pending.values()):
            if not future.done():
                future.set_exception(exc)
        self._pending.clear()
        for waiter in list(self._event_waiters):
            if not waiter.future.done():
                waiter.future.set_exception(exc)
        self._event_waiters.clear()

    @staticmethod
    def _event_predicate_matches(
        event: dict[str, Any],
        predicate: Any,
    ) -> bool:
        if predicate is None:
            return True
        if callable(predicate):
            return bool(predicate(event))
        return True

    def _dispatch_event_waiters(self, event: dict[str, Any]) -> None:
        event_method = str(event.get("method", ""))
        matched: list[EventWaiter] = []
        for waiter in self._event_waiters:
            if waiter.method != event_method:
                continue
            if not self._event_predicate_matches(event, waiter.predicate):
                continue
            matched.append(waiter)

        for waiter in matched:
            if not waiter.future.done():
                waiter.future.set_result(event)
            self._event_waiters.remove(waiter)

    def _track_event(self, event: dict[str, Any]) -> None:
        event_method = str(event.get("method", ""))
        self._events.append(event)
        self._event_count += 1
        self._last_event_method = event_method or None
        if event_method:
            self._event_breakdown[event_method] = self._event_breakdown.get(event_method, 0) + 1
        if event_method == "Page.lifecycleEvent":
            params = event.get("params", {})
            if isinstance(params, dict):
                lifecycle_name = params.get("name")
                if isinstance(lifecycle_name, str) and lifecycle_name.strip():
                    self._lifecycle_state = lifecycle_name
        elif event_method == "Page.loadEventFired":
            self._lifecycle_state = "load"

    def _find_recent_event(self, method: str, predicate: Any = None) -> dict[str, Any] | None:
        for event in reversed(self._events):
            if event.get("method") != method:
                continue
            if self._event_predicate_matches(event, predicate):
                return event
        return None

    async def _reader_loop(self) -> None:
        ws = self._require_ws()
        try:
            while True:
                raw_message = await ws.recv()
                message = json.loads(raw_message)
                if not isinstance(message, dict):
                    continue

                message_id = message.get("id")
                if isinstance(message_id, int):
                    future = self._pending.pop(message_id, None)
                    if future is not None and not future.done():
                        future.set_result(message)
                    else:
                        self._buffered_responses[message_id] = message
                    continue

                self._track_event(message)
                self._dispatch_event_waiters(message)
        except asyncio.CancelledError:
            raise
        except RuntimeError as exc:
            self._fail_pending(exc)
        except StopAsyncIteration:
            if self._pending:
                self._fail_pending(RuntimeError("CDP reader stopped"))
        except (
            json.JSONDecodeError,
            OSError,
            TypeError,
            ValueError,
            WebSocketException,
        ) as exc:
            self._fail_pending(RuntimeError(f"CDP reader stopped: {exc}"))
            logger.error("CDP reader stopped: %s", exc)
        finally:
            self._reader_task = None

    @staticmethod
    def _percentile(latencies: list[float], percentile: float) -> float:
        if not latencies:
            return 0.0
        ordered = sorted(latencies)
        index = max(0, math.ceil(len(ordered) * percentile) - 1)
        return ordered[min(index, len(ordered) - 1)]

    def _record_command(self, command: str, latency_ms: float, *, ok: bool) -> None:
        self._telemetry.append(
            CommandTelemetry(command=command, latency_ms=round(latency_ms, 3), ok=ok)
        )

    def _suggested_delay_s(self) -> float:
        if not self._telemetry:
            return self.base_delay_s
        latencies = [sample.latency_ms for sample in self._telemetry]
        avg_latency_ms = sum(latencies) / len(latencies)
        p95_latency_ms = self._percentile(latencies, 0.95)
        error_count = sum(1 for sample in self._telemetry if not sample.ok)
        error_ratio = error_count / len(self._telemetry)
        adaptive_ms = (avg_latency_ms * 0.25) + (p95_latency_ms * 0.15) + (error_ratio * 150.0)
        suggested = self.base_delay_s + (adaptive_ms / 1000.0)
        return min(suggested, self.max_suggested_delay_s)

    def _ewma_latency_ms(self, alpha: float = 0.4) -> float:
        history = list(self._telemetry)
        if not history:
            return 0.0
        ewma = history[0].latency_ms
        for sample in history[1:]:
            ewma = (alpha * sample.latency_ms) + ((1.0 - alpha) * ewma)
        return ewma

    def _consecutive_errors(self) -> int:
        streak = 0
        for sample in reversed(self._telemetry):
            if sample.ok:
                break
            streak += 1
        return streak

    def _command_breakdown(self) -> dict[str, dict[str, Any]]:
        breakdown: dict[str, dict[str, Any]] = {}
        for sample in self._telemetry:
            bucket = breakdown.setdefault(
                sample.command,
                {"count": 0, "error_count": 0, "latency_total_ms": 0.0, "last_ok": sample.ok},
            )
            bucket["count"] += 1
            bucket["error_count"] += 0 if sample.ok else 1
            bucket["latency_total_ms"] += sample.latency_ms
            bucket["last_ok"] = sample.ok

        return {
            command: {
                "count": values["count"],
                "error_count": values["error_count"],
                "avg_latency_ms": round(values["latency_total_ms"] / values["count"], 3),
                "last_ok": values["last_ok"],
            }
            for command, values in breakdown.items()
        }

    @staticmethod
    def _timeout_deadline(timeout: float | None) -> float | None:
        if timeout is None:
            return None
        return time.monotonic() + max(0.0, timeout)

    @staticmethod
    def _remaining_timeout(deadline: float | None) -> float | None:
        if deadline is None:
            return None
        return max(0.0, deadline - time.monotonic())

    async def _run_compound_action(
        self,
        action: Callable[[], Awaitable[bool]],
        *,
        action_selector: str | None = None,
        lifecycle_name: str | None = None,
        wait_selector: str | None = None,
        wait_text: str | None = None,
        visible: bool = True,
        timeout: float | None = None,
        poll_interval: float = 0.1,
        retry_interval: float = 0.1,
        max_attempts: int = 2,
    ) -> bool:
        """Execute a UI action once it is actionable, with bounded retries on no-op failures."""
        attempts = max(1, max_attempts)
        deadline = self._timeout_deadline(timeout if timeout is not None else self.timeout)
        for attempt in range(attempts):
            if action_selector is not None:
                step_timeout = self._remaining_timeout(deadline)
                if step_timeout is not None and step_timeout <= 0:
                    return False
                if not await self.wait_for_selector(
                    action_selector,
                    timeout=step_timeout,
                    poll_interval=poll_interval,
                    visible=visible,
                ):
                    return False

            if await action():
                return await self.settle(
                    lifecycle_name=lifecycle_name,
                    selector=wait_selector,
                    text=wait_text,
                    visible=visible,
                    timeout=self._remaining_timeout(deadline),
                    poll_interval=poll_interval,
                )

            if attempt + 1 >= attempts:
                return False

            step_timeout = self._remaining_timeout(deadline)
            if step_timeout is not None and step_timeout <= 0:
                return False
            await asyncio.sleep(min(retry_interval, step_timeout) if step_timeout is not None else retry_interval)
        return False

    @staticmethod
    def _pressure_level(score: float) -> str:
        if score >= 0.75:
            return "critical"
        if score >= 0.5:
            return "hot"
        if score >= 0.25:
            return "warm"
        return "cool"

    async def _apply_pacing(self) -> None:
        delay_s = self._suggested_delay_s() if self.adaptive_pacing else self.base_delay_s
        if delay_s > 0:
            await asyncio.sleep(delay_s)

    def capabilities(self) -> dict[str, bool]:
        """Expose the effective operational surface of the CDP controller."""
        return {
            "connected": self.ws is not None,
            "navigation": True,
            "event_wait": True,
            "navigation_wait": True,
            "action_waits": True,
            "selector_wait": True,
            "dom_extraction": True,
            "multi_extract": True,
            "telemetry": True,
            "screenshots": True,
        }

    def kinetics(self) -> dict[str, Any]:
        """Return recent kinetic telemetry for command pacing and diagnostics."""
        history = list(self._telemetry)
        if not history:
            return {
                "connected": self.ws is not None,
                "command_count": 0,
                "error_count": 0,
                "last_command": None,
                "last_latency_ms": 0.0,
                "last_ok": None,
                "avg_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "ewma_latency_ms": 0.0,
                "success_rate": 0.0,
                "pressure_score": 0.0,
                "pressure_level": "cool",
                "consecutive_errors": 0,
                "suggested_delay_ms": round(self.base_delay_s * 1000.0, 3),
                "command_breakdown": {},
                "inflight_count": self._inflight_count,
                "max_inflight_count": self._max_inflight_count,
                "event_count": self._event_count,
                "event_breakdown": dict(self._event_breakdown),
                "last_event_method": self._last_event_method,
                "lifecycle_state": self._lifecycle_state,
                "timeout_count": self._timeout_count,
                "transport_error_count": self._transport_error_count,
                "cdp_error_count": self._cdp_error_count,
                "uptime_s": round(
                    max(0.0, time.monotonic() - self._connected_since) if self._connected_since else 0.0,
                    3,
                ),
            }

        latencies = [sample.latency_ms for sample in history]
        last = history[-1]
        error_count = sum(1 for sample in history if not sample.ok)
        success_rate = (len(history) - error_count) / len(history)
        ewma_latency_ms = self._ewma_latency_ms()
        normalized_latency = min(1.0, ewma_latency_ms / max(self.timeout * 1000.0, 1.0))
        pressure_score = min(1.0, (normalized_latency * 0.65) + ((1.0 - success_rate) * 0.35))
        return {
            "connected": self.ws is not None,
            "command_count": len(history),
            "error_count": error_count,
            "last_command": last.command,
            "last_latency_ms": last.latency_ms,
            "last_ok": last.ok,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 3),
            "p95_latency_ms": round(self._percentile(latencies, 0.95), 3),
            "ewma_latency_ms": round(ewma_latency_ms, 3),
            "success_rate": round(success_rate, 3),
            "pressure_score": round(pressure_score, 3),
            "pressure_level": self._pressure_level(pressure_score),
            "consecutive_errors": self._consecutive_errors(),
            "suggested_delay_ms": round(self._suggested_delay_s() * 1000.0, 3),
            "command_breakdown": self._command_breakdown(),
            "inflight_count": self._inflight_count,
            "max_inflight_count": self._max_inflight_count,
            "event_count": self._event_count,
            "event_breakdown": dict(self._event_breakdown),
            "last_event_method": self._last_event_method,
            "lifecycle_state": self._lifecycle_state,
            "timeout_count": self._timeout_count,
            "transport_error_count": self._transport_error_count,
            "cdp_error_count": self._cdp_error_count,
            "uptime_s": round(
                max(0.0, time.monotonic() - self._connected_since) if self._connected_since else 0.0,
                3,
            ),
        }

    async def connect(self, target_url_substring: str = "") -> bool:
        """Connect to an active Chrome/Edge tab via CDP."""
        try:
            if self.ws is not None or self._reader_task is not None:
                await self.close()

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(f"{self.base_url}/json")
                res.raise_for_status()
                tabs = res.json()

            target = self._find_target_tab(tabs, target_url_substring)
            if not target:
                logger.error("No tab found matching: '%s'", target_url_substring)
                return False

            ws_url = target.get("webSocketDebuggerUrl")
            if not ws_url:
                logger.error("Target tab is missing webSocketDebuggerUrl: %s", target.get("url", ""))
                return False

            self.ws_url = ws_url
            self.ws = await websockets.connect(
                self.ws_url,
                open_timeout=self.timeout,
                close_timeout=self.timeout,
            )
            self._connected_since = time.monotonic()
            self._ensure_reader_task()
            logger.info("Connected to CDP: %s", target.get("url", ""))

            await self.send("Page.enable")
            await self.send("Runtime.enable")
            return True
        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            OSError,
            TypeError,
            ValueError,
            WebSocketException,
        ) as exc:
            self.ws = None
            self.ws_url = None
            logger.error("Connection failed: %s", exc)
            return False

    async def send(self, method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Send a raw CDP command and wait for the matching response."""
        ws = self._require_ws()
        self._ensure_reader_task()
        await self._apply_pacing()
        self.msg_id += 1
        message_id = self.msg_id
        payload = {
            "id": message_id,
            "method": method,
            "params": dict(params or {}),
        }
        started_at = time.perf_counter()
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[message_id] = future
        self._inflight_count += 1
        self._max_inflight_count = max(self._max_inflight_count, self._inflight_count)
        buffered = self._buffered_responses.pop(message_id, None)
        if buffered is not None and not future.done():
            self._pending.pop(message_id, None)
            future.set_result(buffered)
        try:
            async with self._send_lock:
                await ws.send(json.dumps(payload))
            res = await asyncio.wait_for(future, timeout=self.timeout)
        except asyncio.TimeoutError:
            self._pending.pop(message_id, None)
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            self._timeout_count += 1
            self._record_command(method, latency_ms, ok=False)
            logger.error("CDP timeout in %s after %.2fs", method, self.timeout)
            return {}
        except RuntimeError:
            self._pending.pop(message_id, None)
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            self._record_command(method, latency_ms, ok=False)
            raise
        except (OSError, WebSocketException) as exc:
            self._pending.pop(message_id, None)
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            self._transport_error_count += 1
            self._record_command(method, latency_ms, ok=False)
            logger.error("CDP transport error in %s: %s", method, exc)
            return {}
        finally:
            self._inflight_count = max(0, self._inflight_count - 1)
        latency_ms = (time.perf_counter() - started_at) * 1000.0
        if "error" in res:
            self._cdp_error_count += 1
            self._record_command(method, latency_ms, ok=False)
            logger.error("CDP Error in %s: %s", method, res["error"])
            return {}
        self._record_command(method, latency_ms, ok=True)
        return res.get("result", {})

    async def wait_for_event(
        self,
        method: str,
        *,
        predicate: Any = None,
        timeout: float | None = None,
    ) -> dict[str, Any] | None:
        """Wait for an unsolicited CDP event matching the requested method."""
        self._require_ws()
        self._ensure_reader_task()
        recent = self._find_recent_event(method, predicate=predicate)
        if recent is not None:
            return recent

        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        waiter = EventWaiter(method=method, future=future, predicate=predicate)
        self._event_waiters.append(waiter)
        try:
            return await asyncio.wait_for(future, timeout=timeout if timeout is not None else self.timeout)
        finally:
            if waiter in self._event_waiters:
                self._event_waiters.remove(waiter)

    async def wait_for_navigation(
        self,
        *,
        lifecycle_name: str = "load",
        timeout: float | None = None,
    ) -> dict[str, Any] | None:
        """Wait for page navigation to reach the requested lifecycle milestone."""
        if lifecycle_name == "load":
            load_event = self._find_recent_event("Page.loadEventFired")
            if load_event is not None:
                return load_event

        return await self.wait_for_event(
            "Page.lifecycleEvent" if lifecycle_name != "load" else "Page.loadEventFired",
            predicate=(
                None
                if lifecycle_name == "load"
                else lambda event: isinstance(event.get("params"), dict)
                and event["params"].get("name") == lifecycle_name
            ),
            timeout=timeout,
        )

    async def extract_selector(self, selector: str, extract_html: bool = False) -> str | None:
        """Extract text or HTML content from a CSS selector."""
        prop = "outerHTML" if extract_html else "innerText"
        return await self.evaluate(self._selector_expression(selector, prop))

    async def extract_all(
        self,
        selector: str,
        *,
        prop: str = "innerText",
        include_empty: bool = False,
    ) -> list[Any]:
        """Extract a property from all matching elements."""
        selector_literal = self._json_literal(selector)
        prop_literal = self._json_literal(prop)
        filter_clause = "" if include_empty else ".filter((value) => value != null)"
        js = (
            "(() => {"
            f"const nodes = document.querySelectorAll({selector_literal});"
            f"return Array.from(nodes).map((el) => el[{prop_literal}] ?? null){filter_clause};"
            "})()"
        )
        result = await self.evaluate(js)
        return result if isinstance(result, list) else []

    async def extract_page(self, extract_html: bool = False) -> str | None:
        """Extract entire page text or HTML."""
        prop = "outerHTML" if extract_html else "innerText"
        js = f"document.documentElement[{self._json_literal(prop)}]"
        return await self.evaluate(js)

    async def current_url(self) -> str | None:
        """Return the current browser URL."""
        return await self.evaluate("window.location.href")

    async def current_title(self) -> str | None:
        """Return the current document title."""
        return await self.evaluate("document.title")

    async def navigate(self, url: str) -> bool:
        """Navigate the current target to a new URL."""
        result = await self.send("Page.navigate", {"url": url})
        return bool(result.get("frameId"))

    async def exists(self, selector: str) -> bool:
        """Check whether a selector currently resolves in the DOM."""
        return bool(await self.evaluate(self._selector_presence_expression(selector, visible=False)))

    async def wait_for_selector(
        self,
        selector: str,
        *,
        timeout: float | None = None,
        poll_interval: float = 0.1,
        visible: bool = False,
    ) -> bool:
        """Poll until a selector appears, optionally requiring visibility."""
        deadline = time.monotonic() + (timeout if timeout is not None else self.timeout)
        js = self._selector_presence_expression(selector, visible=visible)
        while time.monotonic() <= deadline:
            if await self.evaluate(js):
                return True
            await asyncio.sleep(poll_interval)
        return False

    async def wait_for_text(
        self,
        text: str,
        *,
        selector: str | None = None,
        timeout: float | None = None,
        poll_interval: float = 0.1,
    ) -> bool:
        """Poll until the requested text appears in the page or selector scope."""
        deadline = time.monotonic() + (timeout if timeout is not None else self.timeout)
        js = self._text_presence_expression(text, selector=selector)
        while time.monotonic() <= deadline:
            if await self.evaluate(js):
                return True
            await asyncio.sleep(poll_interval)
        return False

    async def settle(
        self,
        *,
        lifecycle_name: str | None = None,
        selector: str | None = None,
        text: str | None = None,
        visible: bool = True,
        timeout: float | None = None,
        poll_interval: float = 0.1,
    ) -> bool:
        """Wait for post-action readiness using navigation and/or DOM signals."""
        if lifecycle_name is None and selector is None and text is None:
            return True
        deadline = self._timeout_deadline(timeout if timeout is not None else self.timeout)
        try:
            if lifecycle_name is not None:
                step_timeout = self._remaining_timeout(deadline)
                if step_timeout is not None and step_timeout <= 0:
                    return False
                event = await self.wait_for_navigation(
                    lifecycle_name=lifecycle_name,
                    timeout=step_timeout,
                )
                if event is None:
                    return False
            if selector is not None:
                step_timeout = self._remaining_timeout(deadline)
                if step_timeout is not None and step_timeout <= 0:
                    return False
                if not await self.wait_for_selector(
                    selector,
                    timeout=step_timeout,
                    poll_interval=poll_interval,
                    visible=visible,
                ):
                    return False
            if text is not None:
                step_timeout = self._remaining_timeout(deadline)
                if step_timeout is not None and step_timeout <= 0:
                    return False
                if not await self.wait_for_text(
                    text,
                    selector=selector,
                    timeout=step_timeout,
                    poll_interval=poll_interval,
                ):
                    return False
        except asyncio.TimeoutError:
            return False
        return True

    async def navigate_and_wait(
        self,
        url: str,
        *,
        lifecycle_name: str | None = "load",
        wait_selector: str | None = None,
        wait_text: str | None = None,
        visible: bool = True,
        timeout: float | None = None,
        poll_interval: float = 0.1,
        retry_interval: float = 0.1,
        max_attempts: int = 2,
    ) -> bool:
        """Navigate and then block until the requested readiness signals are satisfied."""
        async def perform() -> bool:
            return await self.navigate(url)

        return await self._run_compound_action(
            perform,
            lifecycle_name=lifecycle_name,
            wait_selector=wait_selector,
            wait_text=wait_text,
            visible=visible,
            timeout=timeout,
            poll_interval=poll_interval,
            retry_interval=retry_interval,
            max_attempts=max_attempts,
        )

    async def click(self, selector: str) -> bool:
        """Perform a click on a CSS selector."""
        selector_literal = self._json_literal(selector)
        js = (
            "(() => {"
            f"const el = document.querySelector({selector_literal});"
            "if (!el) { return false; }"
            "if (typeof el.scrollIntoView === 'function') {"
            "el.scrollIntoView({ block: 'center', inline: 'center' });"
            "}"
            "el.click();"
            "return true;"
            "})()"
        )
        return bool(await self.evaluate(js))

    async def click_and_wait(
        self,
        selector: str,
        *,
        lifecycle_name: str | None = None,
        wait_selector: str | None = None,
        wait_text: str | None = None,
        visible: bool = True,
        timeout: float | None = None,
        poll_interval: float = 0.1,
        retry_interval: float = 0.1,
        max_attempts: int = 2,
    ) -> bool:
        """Click an element and wait for navigation or DOM readiness when requested."""
        async def perform() -> bool:
            return await self.click(selector)

        return await self._run_compound_action(
            perform,
            action_selector=selector,
            lifecycle_name=lifecycle_name,
            wait_selector=wait_selector,
            wait_text=wait_text,
            visible=visible,
            timeout=timeout,
            poll_interval=poll_interval,
            retry_interval=retry_interval,
            max_attempts=max_attempts,
        )

    async def type_text(self, selector: str, text: str) -> bool:
        """Perform a type action on a CSS selector by synthesizing events."""
        selector_literal = self._json_literal(selector)
        text_literal = self._json_literal(text)
        js = (
            "(() => {"
            f"const el = document.querySelector({selector_literal});"
            "if (!el) { return false; }"
            "el.focus();"
            f"el.value = {text_literal};"
            "if (el.isContentEditable) {"
            f"el.textContent = {text_literal};"
            "}"
            "el.dispatchEvent(new Event('input', { bubbles: true }));"
            "el.dispatchEvent(new Event('change', { bubbles: true }));"
            "return true;"
            "})()"
        )
        return bool(await self.evaluate(js))

    async def type_text_and_wait(
        self,
        selector: str,
        text: str,
        *,
        lifecycle_name: str | None = None,
        wait_selector: str | None = None,
        wait_text: str | None = None,
        visible: bool = True,
        timeout: float | None = None,
        poll_interval: float = 0.1,
        retry_interval: float = 0.1,
        max_attempts: int = 2,
    ) -> bool:
        """Type into an element and wait for navigation or DOM readiness when requested."""
        async def perform() -> bool:
            return await self.type_text(selector, text)

        return await self._run_compound_action(
            perform,
            action_selector=selector,
            lifecycle_name=lifecycle_name,
            wait_selector=wait_selector,
            wait_text=wait_text,
            visible=visible,
            timeout=timeout,
            poll_interval=poll_interval,
            retry_interval=retry_interval,
            max_attempts=max_attempts,
        )

    async def evaluate(self, js_expression: str) -> Any:
        """Evaluate raw JS and return the result."""
        res = await self.send(
            "Runtime.evaluate",
            {"expression": js_expression, "returnByValue": True},
        )
        result = res.get("result", {})
        if "value" in result:
            return result["value"]
        if "exceptionDetails" in res:
            logger.error("JS Error: %s", res["exceptionDetails"])
        return None

    async def screenshot(self, filepath: str) -> bool:
        """Capture a screenshot of the page."""
        res = await self.send("Page.captureScreenshot", {"format": "png"})
        image_data = res.get("data")
        if not image_data:
            logger.error("Failed to capture screenshot data.")
            return False
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as f:
            f.write(base64.b64decode(image_data))
        logger.info("Screenshot saved to %s", target)
        return True

    async def close(self) -> None:
        self._fail_pending(RuntimeError("CDP websocket closed"))
        reader_task = self._reader_task
        self._reader_task = None
        ws = self.ws
        self.ws = None
        self.ws_url = None
        self._connected_since = None
        if ws is not None:
            with suppress(RuntimeError, OSError, WebSocketException):
                await ws.close()
        if reader_task is not None:
            reader_task.cancel()
            with suppress(asyncio.CancelledError):
                await reader_task
