from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from cortex.routes.admin import create_api_key, export_project


class _DummyFact:
    def __init__(self, project: str, content: str) -> None:
        self.project = project
        self.content = content

    def to_dict(self) -> dict[str, str]:
        return {
            "id": "1",
            "project": self.project,
            "content": self.content,
            "fact_type": "knowledge",
            "tags": [],
            "confidence": "stated",
            "valid_from": "",
            "valid_until": "",
            "source": "test",
        }


class _DummyRequest:
    headers: dict[str, str] = {}


class _DummyAdminManager:
    def __init__(self, existing_keys=None) -> None:
        self._existing_keys = existing_keys or []
        self.create_key = AsyncMock(
            return_value=(
                "ctx_bootstrap_key",
                SimpleNamespace(
                    name="bootstrap",
                    key_prefix="ctx_bootstrap",
                    tenant_id="default",
                ),
            )
        )

    async def list_keys(self):
        return list(self._existing_keys)


@pytest.mark.asyncio
async def test_export_project_recalls_project_facts(tmp_path: Path) -> None:
    engine = AsyncMock()
    engine.recall.return_value = [_DummyFact("proj", "hello export")]
    auth = SimpleNamespace(tenant_id="tenant", permissions=["admin"])

    out = Path("facts.json")
    result = await export_project("proj", _DummyRequest(), str(out), "json", auth, engine)

    engine.recall.assert_awaited_once_with(project="proj", limit=100_000)
    assert out.exists()
    assert result.project == "proj"
    assert result.artifact == str(out.resolve())
    assert "hello export" in out.read_text(encoding="utf-8")
    out.unlink()


@pytest.mark.asyncio
async def test_create_api_key_blocks_remote_bootstrap(monkeypatch) -> None:
    manager = _DummyAdminManager(existing_keys=[])
    monkeypatch.setattr("cortex.routes.admin._get_auth_manager", lambda: manager)
    request = SimpleNamespace(headers={}, client=SimpleNamespace(host="203.0.113.10"))

    with pytest.raises(HTTPException) as excinfo:
        await create_api_key(request, name="bootstrap", tenant_id="default", authorization=None)

    assert excinfo.value.status_code == 403
    manager.create_key.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_api_key_allows_loopback_bootstrap(monkeypatch) -> None:
    manager = _DummyAdminManager(existing_keys=[])
    monkeypatch.setattr("cortex.routes.admin._get_auth_manager", lambda: manager)
    request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))

    result = await create_api_key(request, name="bootstrap", tenant_id="default", authorization=None)

    manager.create_key.assert_awaited_once()
    assert result.key == "ctx_bootstrap_key"
    assert result.tenant_id == "default"
