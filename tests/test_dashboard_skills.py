import io
import zipfile

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cortex.api.deps import get_async_engine
from cortex.auth import require_auth
from cortex.auth.models import AuthResult
from cortex.routes.dashboard import get_dashboard_html, issue_dashboard_action_token, router


class _FakeAsyncEngine:
    def __init__(self) -> None:
        self.store_calls = []
        self.history_rows = [
            {
                "id": 11,
                "project": "metrics",
                "fact_type": "knowledge",
                "source": "api:skills",
                "content": "Canonical KPI snapshot for skill 'hours-saved' at 2026-03-23T10:00:00Z",
                "tags": ["kpi", "skill", "hours-saved"],
                "created_at": "2026-03-23T10:00:01Z",
                "meta": {
                    "skill_name": "hours-saved",
                    "captured_at": "2026-03-23T10:00:00Z",
                    "metrics": {"Hours_Saved": 750000},
                },
            },
            {
                "id": 12,
                "project": "metrics",
                "fact_type": "knowledge",
                "source": "api:skills",
                "content": "Canonical KPI snapshot for skill 'hours-saved' at 2026-03-24T10:00:00Z",
                "tags": ["kpi", "skill", "hours-saved"],
                "created_at": "2026-03-24T10:00:01Z",
                "meta": {
                    "skill_name": "hours-saved",
                    "captured_at": "2026-03-24T10:00:00Z",
                    "metrics": {"Hours_Saved": 1000000},
                },
            },
        ]

    async def history(self, *, project: str, tenant_id: str) -> list[dict]:
        assert project == "metrics"
        assert tenant_id == "tenant-ops"
        return self.history_rows

    async def store(
        self,
        *,
        project: str,
        content: str,
        tenant_id: str,
        fact_type: str,
        tags: list[str],
        source: str,
        meta: dict,
    ) -> int:
        self.store_calls.append(
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
        fact_id = 99
        self.history_rows.append(
            {
                "id": fact_id,
                "project": project,
                "fact_type": fact_type,
                "source": source,
                "content": content,
                "tags": tags,
                "created_at": "2026-03-24T12:00:01Z",
                "meta": meta,
            }
        )
        return fact_id


def test_dashboard_html_bootstraps_kpi_payloads() -> None:
    html = get_dashboard_html(
        [
            {
                "skill_name": "hours-saved",
                "trigger": "hours_saved",
                "metrics": {"Hours_Saved": 1000000},
                "content": "Hours_Saved: 1000000",
                "history": [
                    {
                        "captured_at": "2026-03-23T10:00:00Z",
                        "metrics": {"Hours_Saved": 750000},
                    },
                    {
                        "captured_at": "2026-03-24T10:00:00Z",
                        "metrics": {"Hours_Saved": 1000000},
                    },
                ],
                "snapshot_token": "signed-token",
            }
        ],
        xlsx_export_token="xlsx-token",
    )

    assert "canonical-kpis" in html
    assert "__CORTEX_KPI_BOOTSTRAP__" in html
    assert "xlsx-token" in html
    assert "hours-saved" in html
    assert "1000000" in html
    assert "computeDeltaSummary" in html
    assert "getVisibleHistory" in html
    assert "historyWindowStorageKey" in html
    assert "localStorage.getItem" in html
    assert "localStorage.setItem" in html
    assert "buildExportPayload" in html
    assert "buildCsvExportRows" in html
    assert "buildCsvExportContent" in html
    assert "escapeCsvValue" in html
    assert "copyKpiJson" in html
    assert "copyKpiCsv" in html
    assert "downloadKpiJson" in html
    assert "downloadKpiCsv" in html
    assert "downloadKpiXlsx" in html
    assert "navigator.clipboard.writeText" in html
    assert "URL.createObjectURL" in html
    assert "text/csv;charset=utf-8" in html
    assert "/dashboard/skills/export.xlsx" in html
    assert "Δ " in html
    assert "No prior snapshot" in html
    assert "renderSparkline" in html
    assert "snapshots:" in html
    assert "History Window" in html
    assert "data-history-window=\"3\"" in html
    assert "data-history-window=\"7\"" in html
    assert "data-history-window=\"12\"" in html
    assert "Capture Snapshot" in html
    assert "Copy KPI JSON" in html
    assert "Copy KPI CSV" in html
    assert "Download KPI JSON" in html
    assert "Download KPI CSV" in html
    assert "Download KPI XLSX" in html
    assert "Capture All Snapshots" in html
    assert "captureAllSnapshots" in html
    assert "copy-kpi-json" in html
    assert "copy-kpi-csv" in html
    assert "download-kpi-json" in html
    assert "download-kpi-csv" in html
    assert "download-kpi-xlsx" in html
    assert "capture-all-kpis" in html
    assert "/dashboard/skills/" in html
    assert "KPI skills live" in html


def test_dashboard_route_embeds_bundled_kpis() -> None:
    engine = _FakeAsyncEngine()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_async_engine] = lambda: engine
    app.dependency_overrides[require_auth] = lambda: AuthResult(
        authenticated=True,
        tenant_id="tenant-ops",
        permissions=["read"],
        key_name="test-key",
    )
    client = TestClient(app)

    response = client.get("/dashboard")

    assert response.status_code == 200
    html = response.text
    assert "hours-saved" in html
    assert "ops-kpi" in html
    assert "1000000" in html
    assert "750000" in html
    assert "trend" in html
    assert "vs prev" in html
    assert "window: last" in html
    assert "snapshot_token" in html
    assert "capture-all-status" in html
    assert "copy-kpi-json" in html
    assert "copy-kpi-csv" in html
    assert "download-kpi-json" in html
    assert "download-kpi-csv" in html
    assert "download-kpi-xlsx" in html


def test_dashboard_xlsx_export_route_returns_workbook() -> None:
    engine = _FakeAsyncEngine()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_async_engine] = lambda: engine
    client = TestClient(app)
    token = issue_dashboard_action_token(
        tenant_id="tenant-ops",
        skill_name="__dashboard_export__",
    )

    response = client.get(
        "/dashboard/skills/export.xlsx",
        params={"token": token, "window": 7},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert response.content[:2] == b"PK"

    workbook = zipfile.ZipFile(io.BytesIO(response.content))
    assert "xl/workbook.xml" in workbook.namelist()
    assert "xl/worksheets/sheet1.xml" in workbook.namelist()
    assert "xl/worksheets/sheet2.xml" in workbook.namelist()
    assert "xl/worksheets/sheet3.xml" in workbook.namelist()

    workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
    executive_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    summary_xml = workbook.read("xl/worksheets/sheet2.xml").decode("utf-8")
    history_xml = workbook.read("xl/worksheets/sheet3.xml").decode("utf-8")

    assert "Executive View" in workbook_xml
    assert "KPI Summary" in workbook_xml
    assert "KPI History" in workbook_xml
    assert "hours-saved" in executive_xml
    assert "Hours_Saved" in executive_xml
    assert "33.3%" in executive_xml
    assert "positive" in executive_xml
    assert "hours-saved" in summary_xml
    assert "Hours_Saved" in summary_xml
    assert "2026-03-24T10:00:00Z" in history_xml
    assert "7" in summary_xml


def test_dashboard_snapshot_route_persists_and_returns_updated_payload() -> None:
    engine = _FakeAsyncEngine()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_async_engine] = lambda: engine
    client = TestClient(app)
    token = issue_dashboard_action_token(tenant_id="tenant-ops", skill_name="hours-saved")

    response = client.post(
        "/dashboard/skills/hours-saved/snapshot",
        json={"token": token},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["skill_name"] == "hours-saved"
    assert payload["fact_id"] == 99
    assert payload["latest_snapshot"] is not None
    assert len(payload["history"]) == 3
    assert payload["history"][-1]["metrics"]["Hours_Saved"] == 1000000
    assert engine.store_calls[0]["tenant_id"] == "tenant-ops"
    assert engine.store_calls[0]["source"] == "dashboard:skills"
    assert "dashboard" in engine.store_calls[0]["tags"]


def test_dashboard_snapshot_route_rejects_invalid_token() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_async_engine] = lambda: _FakeAsyncEngine()
    client = TestClient(app)

    response = client.post(
        "/dashboard/skills/hours-saved/snapshot",
        json={"token": "bad.token"},
    )

    assert response.status_code == 403
