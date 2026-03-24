from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine
from cortex.auth.models import AuthResult
from cortex.routes.skills import require_read_permission, require_write_permission, router


class _FakeAsyncEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.history_rows: list[dict[str, Any]] = []

    async def store(
        self,
        *,
        project: str,
        content: str,
        tenant_id: str,
        fact_type: str,
        tags: list[str],
        source: str,
        meta: dict[str, Any],
    ) -> int:
        self.calls.append(
            {
                "project": project,
                "content": content,
                "tenant_id": tenant_id,
                "fact_type": fact_type,
                "tags": tags,
                "source": source,
                "meta": meta,
            }
        )
        return 314

    async def history(self, *, project: str, tenant_id: str) -> list[dict[str, Any]]:
        self.calls.append({"history_project": project, "history_tenant_id": tenant_id})
        return self.history_rows


def _build_client(
    engine: _FakeAsyncEngine | None = None,
    *,
    with_read_auth: bool = True,
) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    if with_read_auth:
        app.dependency_overrides[require_read_permission] = lambda: AuthResult(
            authenticated=True,
            tenant_id="tenant-ops",
            permissions=["read", "write"],
            key_name="test-key",
        )
    if engine is not None:
        app.dependency_overrides[get_async_engine] = lambda: engine
        app.dependency_overrides[require_write_permission] = lambda: AuthResult(
            authenticated=True,
            tenant_id="tenant-ops",
            permissions=["read", "write"],
            key_name="test-key",
        )
    return TestClient(app)


def test_list_skills_requires_read_auth() -> None:
    client = _build_client(with_read_auth=False)

    response = client.get("/v1/skills")

    assert response.status_code == 401


def test_list_skills_filters_kpi_metrics() -> None:
    client = _build_client()

    response = client.get("/v1/skills", params={"category": "metrics", "kpi_only": "true"})

    assert response.status_code == 200
    payload = response.json()
    names = {item["name"] for item in payload}
    assert "hours-saved" in names
    assert "ops-kpi" in names
    assert "cortex-persist" not in names


def test_get_skill_kpi_returns_hours_saved() -> None:
    client = _build_client()

    response = client.get("/v1/skills/hours-saved/kpi")

    assert response.status_code == 200
    payload = response.json()
    assert payload["skill_name"] == "hours-saved"
    assert payload["trigger"] == "hours_saved"
    assert payload["metrics"] == {"Hours_Saved": 1000000}
    assert payload["content"] == "Hours_Saved: 1000000"


def test_get_skill_kpi_returns_ops_bundle() -> None:
    client = _build_client()

    response = client.get("/v1/skills/ops-kpi/kpi")

    assert response.status_code == 200
    payload = response.json()
    assert payload["metrics"] == {
        "Hours_Saved": 1000000,
        "Cost_Saved_EUR": 42000,
        "Tasks_Automated": 144,
    }


def test_get_skill_kpi_rejects_non_kpi_skill() -> None:
    client = _build_client()

    response = client.get("/v1/skills/cortex-persist/kpi")

    assert response.status_code == 400
    assert "does not expose canonical KPIs" in response.json()["detail"]


def test_create_skill_snapshot_persists_fact() -> None:
    engine = _FakeAsyncEngine()
    client = _build_client(engine)

    response = client.post(
        "/v1/skills/ops-kpi/snapshot",
        json={
            "project": "metrics",
            "fact_type": "knowledge",
            "tags": ["daily"],
            "meta": {"snapshot_origin": "api-test"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["fact_id"] == 314
    assert payload["skill_name"] == "ops-kpi"
    assert payload["project"] == "metrics"
    assert payload["metrics"] == {
        "Hours_Saved": 1000000,
        "Cost_Saved_EUR": 42000,
        "Tasks_Automated": 144,
    }
    assert payload["message"] == "KPI snapshot stored"

    assert len(engine.calls) == 1
    call = engine.calls[0]
    assert call["tenant_id"] == "tenant-ops"
    assert call["project"] == "metrics"
    assert call["fact_type"] == "knowledge"
    assert call["source"] == "api:skills"
    assert call["tags"] == ["kpi", "skill", "ops-kpi", "daily"]
    assert call["meta"]["skill_name"] == "ops-kpi"
    assert call["meta"]["trigger"] == "ops_kpi"
    assert call["meta"]["snapshot_origin"] == "api-test"
    assert call["meta"]["metrics"]["Hours_Saved"] == 1000000
    assert "Canonical KPI snapshot for skill 'ops-kpi'" in call["content"]


def test_list_skill_snapshots_returns_history_for_skill() -> None:
    engine = _FakeAsyncEngine()
    engine.history_rows = [
        {
            "id": 12,
            "project": "metrics",
            "fact_type": "knowledge",
            "source": "api:skills",
            "content": "Canonical KPI snapshot for skill 'ops-kpi' at 2026-03-24T11:00:00Z",
            "tags": ["kpi", "skill", "ops-kpi", "daily"],
            "created_at": "2026-03-24T11:00:01Z",
            "meta": {
                "skill_name": "ops-kpi",
                "captured_at": "2026-03-24T11:00:00Z",
                "metrics": {
                    "Hours_Saved": 1000000,
                    "Cost_Saved_EUR": 42000,
                    "Tasks_Automated": 144,
                },
            },
        },
        {
            "id": 9,
            "project": "metrics",
            "fact_type": "knowledge",
            "source": "api:skills",
            "content": "Canonical KPI snapshot for skill 'hours-saved' at 2026-03-23T10:00:00Z",
            "tags": ["kpi", "skill", "hours-saved"],
            "created_at": "2026-03-23T10:00:01Z",
            "meta": {
                "skill_name": "hours-saved",
                "captured_at": "2026-03-23T10:00:00Z",
                "metrics": {"Hours_Saved": 1000000},
            },
        },
    ]
    client = _build_client(engine)

    response = client.get("/v1/skills/ops-kpi/snapshots", params={"project": "metrics", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["fact_id"] == 12
    assert payload[0]["skill_name"] == "ops-kpi"
    assert payload[0]["captured_at"] == "2026-03-24T11:00:00Z"
    assert payload[0]["metrics"]["Tasks_Automated"] == 144
