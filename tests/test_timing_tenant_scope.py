from __future__ import annotations

import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient

import cortex.api.state as api_state
from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.extensions.timing.tracker import TimingTracker
from cortex.routes import timing as timing_routes
from cortex.types.models import TimeSummaryResponse


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE heartbeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL,
            entity TEXT,
            category TEXT NOT NULL,
            branch TEXT,
            language TEXT,
            timestamp TEXT NOT NULL,
            meta TEXT DEFAULT '{}'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL DEFAULT 'default',
            project TEXT NOT NULL,
            category TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_s INTEGER NOT NULL,
            entities TEXT DEFAULT '[]',
            heartbeats INTEGER DEFAULT 0,
            meta TEXT DEFAULT '{}'
        )
        """
    )
    return conn


def test_timing_tracker_separates_tenants_in_daily_summary() -> None:
    conn = _make_conn()
    tracker = TimingTracker(conn)
    tracker.heartbeat(
        project="alpha",
        tenant_id="tenant-a",
        entity="alpha.py",
        timestamp="2026-03-31T10:00:00+00:00",
    )
    tracker.heartbeat(
        project="beta",
        tenant_id="tenant-b",
        entity="beta.py",
        timestamp="2026-03-31T10:01:00+00:00",
    )
    tracker.flush()

    tenant_a = tracker.report(days=1, tenant_id="tenant-a")
    tenant_b = tracker.report(days=1, tenant_id="tenant-b")

    assert tenant_a.by_project == {"alpha": 30}
    assert tenant_b.by_project == {"beta": 30}
    assert tracker.daily(days=1, tenant_id="tenant-a")[-1]["seconds"] == 30
    assert tracker.daily(days=1, tenant_id="tenant-b")[-1]["seconds"] == 30


class _FakeTracker:
    def __init__(self) -> None:
        self.heartbeat_calls: list[dict] = []
        self.today_calls: list[dict] = []
        self.daily_calls: list[dict] = []

    def heartbeat(self, **kwargs) -> int:
        self.heartbeat_calls.append(kwargs)
        return 11

    def flush(self) -> None:
        return None

    def today(self, **kwargs):
        self.today_calls.append(kwargs)
        return TimeSummaryResponse(
            total_seconds=30,
            total_hours=0.01,
            by_category={"coding": 30},
            by_project={"project-alpha": 30},
            entries=1,
            heartbeats=1,
            top_entities=[["alpha.py", 1]],
        )

    def daily(self, **kwargs):
        self.daily_calls.append(kwargs)
        return [{"date": "2026-03-31", "seconds": 30}]


def _client(tracker: _FakeTracker, auth_result: AuthResult) -> TestClient:
    app = FastAPI()
    app.include_router(timing_routes.router)
    app.dependency_overrides[require_auth] = lambda: auth_result
    api_state.tracker = tracker
    return TestClient(app)


def test_timing_routes_pass_tenant_id_without_project_equals_tenant_guard() -> None:
    tracker = _FakeTracker()
    client = _client(
        tracker,
        AuthResult(
            authenticated=True,
            tenant_id="tenant-a",
            permissions=["read", "write"],
            key_name="timing-key",
        ),
    )

    heartbeat = client.post(
        "/v1/heartbeat",
        json={"project": "project-alpha", "entity": "alpha.py"},
    )
    today = client.get("/v1/time/today", params={"project": "project-alpha"})
    history = client.get("/v1/time/history", params={"days": 3})

    assert heartbeat.status_code == 200
    assert today.status_code == 200
    assert history.status_code == 200
    assert tracker.heartbeat_calls == [
        {
            "project": "project-alpha",
            "tenant_id": "tenant-a",
            "entity": "alpha.py",
            "category": None,
            "branch": None,
            "language": None,
            "meta": None,
        }
    ]
    assert tracker.today_calls == [{"project": "project-alpha", "tenant_id": "tenant-a"}]
    assert tracker.daily_calls == [{"days": 3, "tenant_id": "tenant-a"}]
