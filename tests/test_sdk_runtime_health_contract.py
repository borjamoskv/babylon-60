from __future__ import annotations

import sys
from pathlib import Path

import pytest

SDK_ROOT = Path(__file__).resolve().parents[1] / "cortex-sdk"
if str(SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(SDK_ROOT))

from cortex_persist.async_client import AsyncRuntimeClient  # noqa: E402
from cortex_persist.client import RuntimeClient  # noqa: E402


def _payload() -> dict:
    return {
        "status": "degraded",
        "components": {"db": "degraded"},
        "degraded_features": ["db"],
        "warnings": ["db: degraded (40%)"],
        "score": 62.5,
        "grade": "C",
        "summary": "CORTEX Health: 62.5/100",
        "trend": "stable",
        "recommendations": ["compact db"],
        "sub_indices": {"storage": 55.0},
        "component_details": {
            "db": {
                "status": "degraded",
                "value": 40.0,
                "latency_ms": 3.2,
                "description": "db size pressure",
                "remediation": "compact db",
            }
        },
        "checked_at": "2026-04-14T12:00:00+00:00",
    }


def test_runtime_client_health_preserves_extended_runtime_fields() -> None:
    client = RuntimeClient(lambda method, path: _payload())

    report = client.health()

    assert report["status"] == "degraded"
    assert report["score"] == 62.5
    assert report["grade"] == "C"
    assert report["component_details"]["db"]["remediation"] == "compact db"


def test_runtime_client_health_preserves_additive_fields() -> None:
    payload = _payload() | {"collector_revision": 7}
    client = RuntimeClient(lambda method, path: payload)

    report = client.health()

    assert dict(report)["collector_revision"] == 7


@pytest.mark.asyncio
async def test_async_runtime_client_health_preserves_extended_runtime_fields() -> None:
    async def fake_request(method: str, path: str) -> dict:
        return _payload()

    client = AsyncRuntimeClient(fake_request)

    report = await client.health()

    assert report["status"] == "degraded"
    assert report["trend"] == "stable"
    assert report["sub_indices"]["storage"] == 55.0


@pytest.mark.asyncio
async def test_async_runtime_client_health_preserves_additive_fields() -> None:
    payload = _payload() | {"collector_revision": 7}

    async def fake_request(method: str, path: str) -> dict:
        return payload

    client = AsyncRuntimeClient(fake_request)

    report = await client.health()

    assert dict(report)["collector_revision"] == 7
