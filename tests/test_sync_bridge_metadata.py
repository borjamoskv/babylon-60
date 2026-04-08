from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from cortex.crypto.aes import get_default_encrypter
from cortex.extensions.sync.common import RELATION_BRIDGE_KIND, SYSTEM_BRIDGE_KIND
from cortex.extensions.sync.github_bridge import GitHubCortexBridge
from cortex.extensions.sync.write import _bridge_kind, _writeback_bridges


def _mock_transport(routes: dict[str, list]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        for pattern, data in routes.items():
            if pattern in path:
                return httpx.Response(200, json=data)
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.MockTransport(handler)


def _make_issue(number: int, state: str = "open", is_pr: bool = False) -> dict:
    item: dict = {
        "number": number,
        "title": f"Issue {number}",
        "state": state,
        "body": "Bridge body",
        "html_url": f"https://github.com/borjamoskv/testrepo/issues/{number}",
        "labels": [{"name": "sync"}],
        "updated_at": "2026-03-13T12:00:00Z",
        "created_at": "2026-03-13T10:00:00Z",
    }
    if is_pr:
        item["pull_request"] = {
            "url": f"https://api.github.com/repos/borjamoskv/testrepo/pulls/{number}"
        }
    return item


@pytest.fixture
async def engine(tmp_path: Path):
    from cortex.engine import CortexEngine

    db = str(tmp_path / "test_sync_bridge_metadata.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()
    yield e
    await e.close()


@pytest.mark.slow
async def test_github_bridge_stores_external_bridge_kind(engine) -> None:
    repos = [{"full_name": "borjamoskv/testrepo", "fork": False}]
    transport = _mock_transport(
        {
            "/users/borjamoskv/repos": repos,
            "/repos/borjamoskv/testrepo/issues": [_make_issue(7, is_pr=True)],
        }
    )

    bridge = GitHubCortexBridge(engine, token="fake-token", owner="borjamoskv")
    bridge._client = httpx.AsyncClient(transport=transport)

    result = await bridge.sync_all()
    assert result.prs_synced == 1

    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT metadata FROM facts WHERE fact_type = 'bridge' ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()

    meta = get_default_encrypter().decrypt_json(row[0], tenant_id="default")
    assert meta["bridge_kind"] == "external"
    assert meta["bridge_provider"] == "github"
    assert meta["github_type"] == "pr"

    await bridge.close()


@pytest.mark.slow
async def test_memory_bridge_sync_sets_bridge_kind(engine, tmp_path: Path) -> None:
    from cortex.extensions.sync.common import SyncResult
    from cortex.extensions.sync.read import _sync_bridges

    bridge_path = tmp_path / "bridges.jsonl"
    bridge_path.write_text(
        json.dumps(
            {
                "date": "2026-04-04",
                "from": "alpha",
                "to": "beta",
                "pattern": "shared-invariant",
                "note": "local memory bridge",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = SyncResult()
    await _sync_bridges(engine, bridge_path, result)
    assert result.bridges_synced == 1

    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT metadata FROM facts WHERE fact_type = 'bridge' ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()

    meta = get_default_encrypter().decrypt_json(row[0], tenant_id="default")
    assert meta["bridge_kind"] == RELATION_BRIDGE_KIND
    assert meta["bridge_provider"] == "memory"
    assert meta["from"] == "alpha"


@pytest.mark.slow
async def test_migration_bridge_sets_bridge_provider(engine, tmp_path: Path) -> None:
    from cortex.migrate import _migrate_bridges

    bridges_path = tmp_path / "bridges.jsonl"
    bridges_path.write_text(
        json.dumps(
            {
                "date": "2026-04-04T10:00:00Z",
                "from": "left",
                "to": "right",
                "pattern": "legacy-link",
                "note": "migrated bridge",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    stats = {"bridges_imported": 0, "errors": []}
    _migrate_bridges(engine, bridges_path, stats)

    assert stats["bridges_imported"] == 1

    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT metadata FROM facts WHERE fact_type = 'bridge' ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()

    meta = get_default_encrypter().decrypt_json(row[0], tenant_id="default")
    assert meta["bridge_kind"] == RELATION_BRIDGE_KIND
    assert meta["bridge_provider"] == "memory"


@pytest.mark.slow
async def test_writeback_bridges_skips_external_and_legacy_github(engine, tmp_path: Path, monkeypatch) -> None:
    from cortex.extensions.sync.common import WritebackResult
    from cortex.extensions.sync import write as sync_write

    monkeypatch.setattr(sync_write, "runtime_memory_dir", lambda: tmp_path)

    await engine.store(
        project="__bridges__",
        content="BRIDGE: alpha → beta | Patrón: shared | Nota: local",
        fact_type="bridge",
        tags=["alpha", "beta", "shared"],
        confidence="verified",
        source="sync-agent-memory",
        meta={
            "bridge_kind": RELATION_BRIDGE_KIND,
            "from": "alpha",
            "to": "beta",
            "pattern": "shared",
            "note": "local",
        },
    )
    await engine.store(
        project="github-sync",
        content="[GitHub Issue] borjamoskv/testrepo#9: Issue 9. Bridge body",
        fact_type="bridge",
        tags=["github", "issue", "testrepo"],
        confidence="C4",
        source="bridge:github",
        meta={
            "bridge_kind": "external",
            "bridge_provider": "github",
            "github_key": "abc123",
            "github_repo": "borjamoskv/testrepo",
        },
    )
    await engine.store(
        project="github-sync",
        content="[GitHub Issue] borjamoskv/testrepo#10: Issue 10. Bridge body",
        fact_type="bridge",
        tags=["github", "issue", "testrepo"],
        confidence="C4",
        source="bridge:github",
        meta={
            "github_key": "legacy123",
            "github_repo": "borjamoskv/testrepo",
        },
    )

    result = WritebackResult()
    await _writeback_bridges(engine, result)

    exported = (tmp_path / "bridges.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(exported) == 1

    entry = json.loads(exported[0])
    assert entry["from"] == "alpha"
    assert entry["to"] == "beta"
    assert entry["bridge_kind"] == RELATION_BRIDGE_KIND
    assert result.items_exported == 1


@pytest.mark.slow
async def test_writeback_bridges_skips_system_bridge_kind(engine, tmp_path: Path, monkeypatch) -> None:
    from cortex.extensions.sync.common import WritebackResult
    from cortex.extensions.sync import write as sync_write

    monkeypatch.setattr(sync_write, "runtime_memory_dir", lambda: tmp_path)

    await engine.store(
        project="SYSTEM",
        content="Connectivity audit",
        fact_type="bridge",
        source="agent:apis-omega",
        meta={
            "bridge_kind": SYSTEM_BRIDGE_KIND,
            "bridge_provider": "apis_omega",
            "sub_type": "connectivity_audit",
        },
    )

    result = WritebackResult()
    await _writeback_bridges(engine, result)

    exported_path = tmp_path / "bridges.jsonl"
    assert exported_path.exists()
    assert exported_path.read_text(encoding="utf-8") == ""
    assert result.items_exported == 0


def test_bridge_kind_infers_external_for_legacy_github_rows() -> None:
    assert _bridge_kind({"github_key": "repo#1"}, "bridge:github") == "external"
    assert _bridge_kind({"bridge_kind": RELATION_BRIDGE_KIND}, "sync-agent-memory") == "relation"
