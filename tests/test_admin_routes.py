from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cortex.routes.admin import export_project


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
