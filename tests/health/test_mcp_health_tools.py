from __future__ import annotations

from types import SimpleNamespace

import pytest

from cortex.mcp.health_tools import register_health_tools


class _FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return decorator


@pytest.mark.asyncio
async def test_register_health_tools_uses_canonical_serialization(monkeypatch) -> None:
    mcp = _FakeMCP()
    register_health_tools(mcp, SimpleNamespace(cfg=SimpleNamespace(db_path="/tmp/test-health.db")))

    from cortex.extensions.health import Grade, HealthScore

    monkeypatch.setattr(
        "cortex.extensions.health.collect_health_score",
        lambda db_path: HealthScore(score=72.5, grade=Grade.GOOD),
    )

    result = await mcp.tools["cortex_health_check"]()

    assert result["grade"] == "B"
    assert isinstance(result["summary"], str)


@pytest.mark.asyncio
async def test_register_health_tools_report_uses_canonical_builder(monkeypatch) -> None:
    mcp = _FakeMCP()
    register_health_tools(mcp, SimpleNamespace(cfg=SimpleNamespace(db_path="/tmp/test-health.db")))

    class _FakeReport:
        def to_dict(self) -> dict:
            return {
                "score": {"score": 91.0, "grade": "A", "healthy": True, "timestamp": "now"},
                "recommendations": [],
                "warnings": [],
                "trend": "stable",
                "is_critical": False,
                "db_path": "/tmp/test-health.db",
            }

    monkeypatch.setattr(
        "cortex.extensions.health.build_health_report",
        lambda db_path: _FakeReport(),
    )

    result = await mcp.tools["cortex_health_report"]()

    assert result["score"]["grade"] == "A"
    assert result["trend"] == "stable"


@pytest.mark.asyncio
async def test_register_health_tools_prefers_cfg_db_path(monkeypatch) -> None:
    mcp = _FakeMCP()
    register_health_tools(
        mcp,
        SimpleNamespace(
            db_path="/tmp/wrong.db",
            cfg=SimpleNamespace(db_path="/tmp/right.db"),
        ),
    )

    captured: dict[str, str] = {}

    from cortex.extensions.health import Grade, HealthScore

    def fake_collect(db_path: str):
        captured["db_path"] = db_path
        return HealthScore(score=95.0, grade=Grade.SOVEREIGN)

    monkeypatch.setattr("cortex.extensions.health.collect_health_score", fake_collect)

    result = await mcp.tools["cortex_health_check"]()

    assert captured["db_path"] == "/tmp/right.db"
    assert result["grade"] == "S"


@pytest.mark.asyncio
async def test_register_health_tools_normalizes_db_path(monkeypatch) -> None:
    mcp = _FakeMCP()
    register_health_tools(
        mcp,
        SimpleNamespace(cfg=SimpleNamespace(db_path="~/.cortex/cortex.db")),
    )

    captured: dict[str, str] = {}

    from cortex.extensions.health import Grade, HealthScore

    def fake_collect(db_path: str):
        captured["db_path"] = db_path
        return HealthScore(score=95.0, grade=Grade.SOVEREIGN)

    monkeypatch.setattr("cortex.extensions.health.collect_health_score", fake_collect)

    await mcp.tools["cortex_health_check"]()

    assert captured["db_path"].startswith("/")
    assert captured["db_path"].endswith("/.cortex/cortex.db")


@pytest.mark.asyncio
async def test_register_health_tools_treats_none_cfg_db_path_as_empty(monkeypatch) -> None:
    mcp = _FakeMCP()
    register_health_tools(mcp, SimpleNamespace(cfg=SimpleNamespace(db_path=None)))

    captured: dict[str, str] = {}

    from cortex.extensions.health import Grade, HealthScore

    def fake_collect(db_path: str):
        captured["db_path"] = db_path
        return HealthScore(score=80.0, grade=Grade.EXCELLENT)

    monkeypatch.setattr("cortex.extensions.health.collect_health_score", fake_collect)

    await mcp.tools["cortex_health_check"]()

    assert captured["db_path"] == ""
