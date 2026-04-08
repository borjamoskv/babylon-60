from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from scripts.mac_control.cdp_engine import MacControlOmega


@pytest.mark.asyncio
async def test_send_requires_active_websocket() -> None:
    ctl = MacControlOmega()

    with pytest.raises(RuntimeError, match="not connected"):
        await ctl.send("Runtime.enable")


@pytest.mark.asyncio
async def test_extract_selector_builds_null_safe_js() -> None:
    ctl = MacControlOmega()
    ctl.evaluate = AsyncMock(return_value=None)  # type: ignore[method-assign]
    selector = "button[data-label='Say \"hi\"']"

    await ctl.extract_selector(selector)

    js = ctl.evaluate.await_args.args[0]
    assert f"document.querySelector({json.dumps(selector)})" in js
    assert "if (!el) { return null; }" in js
    assert 'return el["innerText"] ?? null;' in js


@pytest.mark.asyncio
async def test_type_text_uses_json_serialization_for_payloads() -> None:
    ctl = MacControlOmega()
    ctl.evaluate = AsyncMock(return_value=True)  # type: ignore[method-assign]
    selector = 'textarea[name="notes"]'
    text = 'He said "hola"\nnext\\path'

    result = await ctl.type_text(selector, text)

    js = ctl.evaluate.await_args.args[0]
    assert result is True
    assert f"document.querySelector({json.dumps(selector)})" in js
    assert f"el.value = {json.dumps(text)};" in js
    assert "el.isContentEditable" in js
    assert f"el.textContent = {json.dumps(text)};" in js


@pytest.mark.asyncio
async def test_extract_all_builds_array_expression() -> None:
    ctl = MacControlOmega()
    ctl.evaluate = AsyncMock(return_value=["one", "two"])  # type: ignore[method-assign]
    selector = ".item[data-kind='result']"

    result = await ctl.extract_all(selector)

    js = ctl.evaluate.await_args.args[0]
    assert result == ["one", "two"]
    assert f"document.querySelectorAll({json.dumps(selector)})" in js
    assert "Array.from" in js
    assert "filter((value) => value != null)" in js


@pytest.mark.asyncio
async def test_wait_for_selector_polls_until_visible(monkeypatch) -> None:
    ctl = MacControlOmega(timeout=0.3)
    ctl.evaluate = AsyncMock(side_effect=[False, False, True])  # type: ignore[method-assign]
    sleep_mock = AsyncMock()
    monkeypatch.setattr("scripts.mac_control.cdp_engine.asyncio.sleep", sleep_mock)

    found = await ctl.wait_for_selector("#ready", timeout=0.2, poll_interval=0.05, visible=True)

    js = ctl.evaluate.await_args_list[0].args[0]
    assert found is True
    assert ctl.evaluate.await_count == 3
    assert sleep_mock.await_count == 2
    assert 'document.querySelector("#ready")' in js
    assert "getBoundingClientRect" in js


@pytest.mark.asyncio
async def test_navigate_uses_page_domain() -> None:
    ctl = MacControlOmega()
    ctl.send = AsyncMock(return_value={"frameId": "frame-1"})  # type: ignore[method-assign]

    result = await ctl.navigate("https://example.com/dashboard")

    assert result is True
    assert ctl.send.await_args.args == (
        "Page.navigate",
        {"url": "https://example.com/dashboard"},
    )


@pytest.mark.asyncio
async def test_capabilities_report_feature_flags() -> None:
    ctl = MacControlOmega()

    caps = ctl.capabilities()

    assert caps["connected"] is False
    assert caps["navigation"] is True
    assert caps["action_waits"] is True
    assert caps["selector_wait"] is True
    assert caps["telemetry"] is True


@pytest.mark.asyncio
async def test_settle_composes_navigation_selector_and_text_waits() -> None:
    ctl = MacControlOmega()
    ctl.wait_for_navigation = AsyncMock(  # type: ignore[method-assign]
        return_value={"method": "Page.lifecycleEvent", "params": {"name": "networkIdle"}}
    )
    ctl.wait_for_selector = AsyncMock(return_value=True)  # type: ignore[method-assign]
    ctl.wait_for_text = AsyncMock(return_value=True)  # type: ignore[method-assign]

    settled = await ctl.settle(
        lifecycle_name="networkIdle",
        selector="#ready",
        text="Dashboard ready",
        visible=True,
        timeout=0.4,
        poll_interval=0.05,
    )

    assert settled is True
    assert ctl.wait_for_navigation.await_args.kwargs["lifecycle_name"] == "networkIdle"
    assert ctl.wait_for_navigation.await_args.kwargs["timeout"] == pytest.approx(0.4, rel=1e-3)
    assert ctl.wait_for_selector.await_args.kwargs["timeout"] == pytest.approx(0.4, rel=1e-3)
    assert ctl.wait_for_selector.await_args.kwargs["poll_interval"] == 0.05
    assert ctl.wait_for_selector.await_args.kwargs["visible"] is True
    assert ctl.wait_for_text.await_args.kwargs["selector"] == "#ready"
    assert ctl.wait_for_text.await_args.kwargs["timeout"] == pytest.approx(0.4, rel=1e-3)
    assert ctl.wait_for_text.await_args.kwargs["poll_interval"] == 0.05


@pytest.mark.asyncio
async def test_settle_uses_shared_timeout_budget(monkeypatch) -> None:
    ctl = MacControlOmega(timeout=1.0)
    ctl.wait_for_navigation = AsyncMock(  # type: ignore[method-assign]
        return_value={"method": "Page.lifecycleEvent", "params": {"name": "networkIdle"}}
    )
    ctl.wait_for_selector = AsyncMock(return_value=True)  # type: ignore[method-assign]
    ctl.wait_for_text = AsyncMock(return_value=True)  # type: ignore[method-assign]
    remaining = iter([0.8, 0.4, 0.15])
    monkeypatch.setattr(
        MacControlOmega,
        "_timeout_deadline",
        staticmethod(lambda timeout: 101.0 if timeout is not None else None),
    )
    monkeypatch.setattr(
        MacControlOmega,
        "_remaining_timeout",
        staticmethod(lambda deadline: next(remaining)),
    )

    settled = await ctl.settle(
        lifecycle_name="networkIdle",
        selector="#ready",
        text="Dashboard ready",
        timeout=1.0,
    )

    assert settled is True
    assert ctl.wait_for_navigation.await_args.kwargs["timeout"] == pytest.approx(0.8, rel=1e-3)
    assert ctl.wait_for_selector.await_args.kwargs["timeout"] == pytest.approx(0.4, rel=1e-3)
    assert ctl.wait_for_text.await_args.kwargs["timeout"] == pytest.approx(0.15, rel=1e-3)


@pytest.mark.asyncio
async def test_settle_returns_false_on_navigation_timeout() -> None:
    ctl = MacControlOmega()
    ctl.wait_for_navigation = AsyncMock(side_effect=asyncio.TimeoutError)  # type: ignore[method-assign]
    ctl.wait_for_selector = AsyncMock(return_value=True)  # type: ignore[method-assign]

    settled = await ctl.settle(lifecycle_name="load", selector="#ready")

    assert settled is False
    ctl.wait_for_selector.assert_not_called()


@pytest.mark.asyncio
async def test_navigate_and_wait_short_circuits_failed_navigation() -> None:
    ctl = MacControlOmega()
    ctl.navigate = AsyncMock(return_value=False)  # type: ignore[method-assign]
    ctl.settle = AsyncMock(return_value=True)  # type: ignore[method-assign]

    completed = await ctl.navigate_and_wait("https://example.com/dashboard", wait_selector="#ready")

    assert completed is False
    ctl.settle.assert_not_called()


@pytest.mark.asyncio
async def test_click_and_wait_uses_compound_runner() -> None:
    ctl = MacControlOmega()
    ctl.click = AsyncMock(return_value=True)  # type: ignore[method-assign]
    ctl._run_compound_action = AsyncMock(return_value=True)  # type: ignore[method-assign]

    completed = await ctl.click_and_wait(
        "#submit",
        lifecycle_name="networkIdle",
        wait_selector="#toast",
        wait_text="Saved",
        timeout=0.6,
    )

    assert completed is True
    assert ctl._run_compound_action.await_args.kwargs == {
        "action_selector": "#submit",
        "lifecycle_name": "networkIdle",
        "wait_selector": "#toast",
        "wait_text": "Saved",
        "visible": True,
        "timeout": 0.6,
        "poll_interval": 0.1,
        "retry_interval": 0.1,
        "max_attempts": 2,
    }


@pytest.mark.asyncio
async def test_type_text_and_wait_uses_compound_runner() -> None:
    ctl = MacControlOmega()
    ctl.type_text = AsyncMock(return_value=True)  # type: ignore[method-assign]
    ctl._run_compound_action = AsyncMock(return_value=True)  # type: ignore[method-assign]

    completed = await ctl.type_text_and_wait(
        "#notes",
        "hola",
        wait_selector="#status",
        wait_text="Saved",
        timeout=0.5,
    )

    assert completed is True
    assert ctl._run_compound_action.await_args.kwargs == {
        "action_selector": "#notes",
        "lifecycle_name": None,
        "wait_selector": "#status",
        "wait_text": "Saved",
        "visible": True,
        "timeout": 0.5,
        "poll_interval": 0.1,
        "retry_interval": 0.1,
        "max_attempts": 2,
    }


@pytest.mark.asyncio
async def test_send_ignores_unsolicited_events_until_matching_id() -> None:
    ctl = MacControlOmega()
    ws = AsyncMock()
    ws.recv = AsyncMock(
        side_effect=[
            json.dumps({"method": "Page.loadEventFired", "params": {"timestamp": 1}}),
            json.dumps({"id": 1, "result": {"ok": True}}),
        ]
    )
    ctl.ws = ws

    result = await ctl.send("Runtime.enable")

    assert result == {"ok": True}
    payload = json.loads(ws.send.await_args.args[0])
    assert payload == {"id": 1, "method": "Runtime.enable", "params": {}}


@pytest.mark.asyncio
async def test_send_dispatches_concurrent_responses_by_id() -> None:
    ctl = MacControlOmega()
    ws = _QueuedWebSocket()
    ctl.ws = ws

    runtime_task = asyncio.create_task(ctl.send("Runtime.enable"))
    page_task = asyncio.create_task(ctl.send("Page.enable"))

    while len(ws.sent_payloads) < 2:
        await asyncio.sleep(0)

    sent_by_method = {payload["method"]: int(payload["id"]) for payload in ws.sent_payloads}
    await ws.push({"id": sent_by_method["Page.enable"], "result": {"page": True}})
    await ws.push({"id": sent_by_method["Runtime.enable"], "result": {"runtime": True}})

    results = await asyncio.wait_for(asyncio.gather(runtime_task, page_task), timeout=1.0)

    assert results == [{"runtime": True}, {"page": True}]


@pytest.mark.asyncio
async def test_close_releases_pending_requests_without_hanging() -> None:
    ctl = MacControlOmega()
    ws = _QueuedWebSocket()
    ctl.ws = ws

    pending = asyncio.create_task(ctl.send("Runtime.enable"))
    while len(ws.sent_payloads) < 1:
        await asyncio.sleep(0)

    await ctl.close()

    with pytest.raises(RuntimeError, match="CDP websocket closed"):
        await asyncio.wait_for(pending, timeout=1.0)


@pytest.mark.asyncio
async def test_wait_for_event_resolves_unsolicited_message() -> None:
    ctl = MacControlOmega()
    ws = _QueuedWebSocket()
    ctl.ws = ws

    waiter = asyncio.create_task(ctl.wait_for_event("Page.loadEventFired"))
    await asyncio.sleep(0)
    await ws.push({"method": "Page.loadEventFired", "params": {"timestamp": 1}})

    event = await asyncio.wait_for(waiter, timeout=1.0)

    assert event == {"method": "Page.loadEventFired", "params": {"timestamp": 1}}
    assert ctl.kinetics()["last_event_method"] == "Page.loadEventFired"
    await ctl.close()


@pytest.mark.asyncio
async def test_wait_for_navigation_tracks_lifecycle_state() -> None:
    ctl = MacControlOmega()
    ws = _QueuedWebSocket()
    ctl.ws = ws

    waiter = asyncio.create_task(ctl.wait_for_navigation(lifecycle_name="networkIdle"))
    await asyncio.sleep(0)
    await ws.push({"method": "Page.lifecycleEvent", "params": {"name": "networkIdle"}})

    event = await asyncio.wait_for(waiter, timeout=1.0)
    kinetics = ctl.kinetics()

    assert event == {"method": "Page.lifecycleEvent", "params": {"name": "networkIdle"}}
    assert kinetics["lifecycle_state"] == "networkIdle"
    assert kinetics["event_breakdown"]["Page.lifecycleEvent"] == 1
    await ctl.close()


@pytest.mark.asyncio
async def test_kinetics_tracks_inflight_and_event_counts() -> None:
    ctl = MacControlOmega()
    ws = _QueuedWebSocket()
    ctl.ws = ws

    runtime_task = asyncio.create_task(ctl.send("Runtime.enable"))
    page_task = asyncio.create_task(ctl.send("Page.enable"))

    while len(ws.sent_payloads) < 2:
        await asyncio.sleep(0)

    await ws.push({"method": "Page.frameStartedLoading", "params": {"frameId": "f-1"}})
    await asyncio.sleep(0)
    warm_kinetics = ctl.kinetics()

    assert warm_kinetics["inflight_count"] == 2
    assert warm_kinetics["max_inflight_count"] == 2
    assert warm_kinetics["event_count"] == 1
    assert warm_kinetics["last_event_method"] == "Page.frameStartedLoading"

    sent_by_method = {payload["method"]: int(payload["id"]) for payload in ws.sent_payloads}
    await ws.push({"id": sent_by_method["Runtime.enable"], "result": {"runtime": True}})
    await ws.push({"id": sent_by_method["Page.enable"], "result": {"page": True}})
    await asyncio.gather(runtime_task, page_task)

    cooled_kinetics = ctl.kinetics()
    assert cooled_kinetics["inflight_count"] == 0
    assert cooled_kinetics["max_inflight_count"] == 2
    await ctl.close()


@pytest.mark.asyncio
async def test_send_tracks_kinetic_metrics(monkeypatch) -> None:
    ctl = MacControlOmega()
    ws = AsyncMock()
    ws.recv = AsyncMock(
        side_effect=[
            json.dumps({"id": 1, "result": {"ok": True}}),
            json.dumps({"id": 2, "error": {"message": "boom"}}),
        ]
    )
    ctl.ws = ws

    perf_counter_values = iter([100.0, 100.012, 200.0, 200.050])
    monkeypatch.setattr(
        "scripts.mac_control.cdp_engine.time.perf_counter",
        lambda: next(perf_counter_values),
    )

    first = await ctl.send("Runtime.enable")
    second = await ctl.send("Page.reload")
    kinetics = ctl.kinetics()

    assert first == {"ok": True}
    assert second == {}
    assert kinetics["command_count"] == 2
    assert kinetics["error_count"] == 1
    assert kinetics["last_command"] == "Page.reload"
    assert kinetics["last_ok"] is False
    assert kinetics["avg_latency_ms"] == pytest.approx(31.0)
    assert kinetics["p95_latency_ms"] == pytest.approx(50.0)
    assert kinetics["suggested_delay_ms"] > 0


@pytest.mark.asyncio
async def test_kinetics_exposes_pressure_and_command_breakdown(monkeypatch) -> None:
    ctl = MacControlOmega(timeout=0.1)
    ws = AsyncMock()
    ws.recv = AsyncMock(
        side_effect=[
            json.dumps({"id": 1, "result": {"ok": True}}),
            json.dumps({"id": 2, "result": {"ok": True}}),
            json.dumps({"id": 3, "error": {"message": "boom"}}),
        ]
    )
    ctl.ws = ws

    perf_counter_values = iter([10.0, 10.020, 20.0, 20.040, 30.0, 30.090])
    monkeypatch.setattr(
        "scripts.mac_control.cdp_engine.time.perf_counter",
        lambda: next(perf_counter_values),
    )

    await ctl.send("Runtime.enable")
    await ctl.send("Runtime.enable")
    await ctl.send("Page.reload")
    kinetics = ctl.kinetics()

    assert kinetics["success_rate"] == pytest.approx(2 / 3, rel=1e-3)
    assert kinetics["ewma_latency_ms"] == pytest.approx(52.8, rel=1e-3)
    assert 0.0 < kinetics["pressure_score"] <= 1.0
    assert kinetics["pressure_level"] == "warm"
    assert kinetics["consecutive_errors"] == 1
    assert kinetics["command_breakdown"]["Runtime.enable"] == {
        "count": 2,
        "error_count": 0,
        "avg_latency_ms": pytest.approx(30.0),
        "last_ok": True,
    }
    assert kinetics["command_breakdown"]["Page.reload"] == {
        "count": 1,
        "error_count": 1,
        "avg_latency_ms": pytest.approx(90.0),
        "last_ok": False,
    }


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.requests: list[str] = []

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, url: str) -> _FakeResponse:
        self.requests.append(url)
        return _FakeResponse(self.payload)


class _QueuedWebSocket:
    def __init__(self) -> None:
        self.sent_payloads: list[dict[str, object]] = []
        self._recv_queue: asyncio.Queue[object] = asyncio.Queue()

    async def send(self, payload: str) -> None:
        self.sent_payloads.append(json.loads(payload))

    async def recv(self) -> str:
        item = await self._recv_queue.get()
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, str):
            return item
        return json.dumps(item)

    async def close(self) -> None:
        await self._recv_queue.put(RuntimeError("CDP websocket closed"))

    async def push(self, payload: dict[str, object] | str | BaseException) -> None:
        await self._recv_queue.put(payload)


@pytest.mark.asyncio
async def test_connect_reuses_existing_session_and_matches_title(monkeypatch) -> None:
    old_ws = AsyncMock()
    new_ws = AsyncMock()
    client = _FakeAsyncClient(
        [
            {
                "type": "page",
                "title": "Control Total Dashboard",
                "url": "https://example.com/app",
                "webSocketDebuggerUrl": "ws://cdp/new",
            }
        ]
    )

    monkeypatch.setattr(
        "scripts.mac_control.cdp_engine.httpx.AsyncClient",
        lambda timeout: client,
    )
    connect_mock = AsyncMock(return_value=new_ws)
    monkeypatch.setattr("scripts.mac_control.cdp_engine.websockets.connect", connect_mock)

    ctl = MacControlOmega()
    ctl.ws = old_ws
    ctl.send = AsyncMock(return_value={})  # type: ignore[method-assign]

    connected = await ctl.connect("dashboard")

    assert connected is True
    old_ws.close.assert_awaited_once()
    connect_mock.assert_awaited_once_with(
        "ws://cdp/new",
        open_timeout=ctl.timeout,
        close_timeout=ctl.timeout,
    )
    assert ctl.ws is new_ws
    assert ctl.ws_url == "ws://cdp/new"
    assert client.requests == [f"{ctl.base_url}/json"]
    assert ctl.send.await_args_list[0].args == ("Page.enable",)
    assert ctl.send.await_args_list[1].args == ("Runtime.enable",)


@pytest.mark.asyncio
async def test_connect_rejects_non_list_cdp_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.mac_control.cdp_engine.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient({"type": "page"}),
    )
    connect_mock = AsyncMock()
    monkeypatch.setattr("scripts.mac_control.cdp_engine.websockets.connect", connect_mock)

    ctl = MacControlOmega()

    connected = await ctl.connect("anything")

    assert connected is False
    assert ctl.ws is None
    assert ctl.ws_url is None
    connect_mock.assert_not_called()


@pytest.mark.asyncio
async def test_screenshot_creates_parent_directory(tmp_path: Path) -> None:
    ctl = MacControlOmega()
    png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a4s8AAAAASUVORK5CYII="
    ctl.send = AsyncMock(return_value={"data": png})  # type: ignore[method-assign]

    target = tmp_path / "nested" / "capture.png"
    saved = await ctl.screenshot(str(target))

    assert saved is True
    assert target.exists()
    assert target.read_bytes()


@pytest.mark.asyncio
async def test_close_resets_connection_state() -> None:
    ctl = MacControlOmega()
    ws = AsyncMock()
    ctl.ws = ws
    ctl.ws_url = "ws://cdp/current"

    await ctl.close()

    ws.close.assert_awaited_once()
    assert ctl.ws is None
    assert ctl.ws_url is None
