"""Tests for sync bridge import/export normalization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import cortex.extensions.sync as sync_pkg
from cortex.crypto.aes import load_json_dict
from cortex.extensions.sync.read import sync_memory
from cortex.extensions.sync.write import export_to_json


@pytest.fixture
async def engine(tmp_path: Path):
    from cortex.engine import CortexEngine

    db = str(tmp_path / "test_sync_bridges.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()
    yield e
    await e.close()


@pytest.fixture
def sync_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    monkeypatch.setattr(sync_pkg, "MEMORY_DIR", memory_dir)
    monkeypatch.setattr(sync_pkg, "SYNC_STATE_FILE", tmp_path / "sync_state.json")
    return memory_dir


async def test_sync_memory_normalizes_legacy_bridge_kind(engine, sync_paths: Path):
    bridges_path = sync_paths / "bridges.jsonl"
    bridges_path.write_text(
        json.dumps(
            {
                "date": "2026-04-04T10:00:00Z",
                "from": "alpha",
                "to": "beta",
                "pattern": "shared-cache",
                "note": "legacy bridge entry",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = await sync_memory(engine)

    assert result.bridges_synced == 1

    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT metadata FROM facts WHERE fact_type = 'bridge' AND valid_until IS NULL"
        )
        row = await cursor.fetchone()

    assert row is not None
    meta = load_json_dict(row[0], tenant_id="default")
    assert meta["bridge_kind"] == "relation"
    assert meta["bridge_provider"] == "memory"


async def test_sync_memory_skips_non_relation_bridge_kind(engine, sync_paths: Path):
    bridges_path = sync_paths / "bridges.jsonl"
    bridges_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "date": "2026-04-04T10:00:00Z",
                        "from": "alpha",
                        "to": "beta",
                        "pattern": "shared-cache",
                        "note": "relation bridge entry",
                    }
                ),
                json.dumps(
                    {
                        "date": "2026-04-04T11:00:00Z",
                        "from": "gamma",
                        "to": "delta",
                        "pattern": "github",
                        "note": "external bridge entry",
                        "bridge_kind": "external",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = await sync_memory(engine)

    assert result.bridges_synced == 1

    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM facts WHERE fact_type = 'bridge' AND valid_until IS NULL"
        )
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == 1


async def test_export_to_json_only_round_trips_relation_bridges(engine, sync_paths: Path):
    await engine.store(
        project="__bridges__",
        content="BRIDGE: alpha → beta | Patrón: shared-cache | Nota: legacy",
        fact_type="bridge",
        tags=["alpha", "beta", "shared-cache"],
        source="sync-agent-memory",
        meta={
            "date": "2026-04-04T10:00:00Z",
            "from": "alpha",
            "to": "beta",
            "pattern": "shared-cache",
            "note": "legacy",
        },
    )
    await engine.store(
        project="__bridges__",
        content="BRIDGE: gamma → delta | Patrón: relation | Nota: explicit",
        fact_type="bridge",
        tags=["gamma", "delta", "relation"],
        source="sync-agent-memory",
        meta={
            "date": "2026-04-04T11:00:00Z",
            "from": "gamma",
            "to": "delta",
            "pattern": "relation",
            "note": "explicit",
            "bridge_kind": "relation",
        },
    )
    await engine.store(
        project="__bridges__",
        content="BRIDGE: repo → issue | Patrón: github | Nota: external",
        fact_type="bridge",
        tags=["repo", "issue", "github"],
        source="bridge:github",
        meta={
            "date": "2026-04-04T12:00:00Z",
            "from": "repo",
            "to": "issue",
            "pattern": "github",
            "note": "external",
            "github_key": "repo#1",
        },
    )

    result = await export_to_json(engine)

    assert result.files_written >= 1

    lines = (sync_paths / "bridges.jsonl").read_text(encoding="utf-8").strip().splitlines()
    entries = [json.loads(line) for line in lines]

    assert len(entries) == 2
    assert {(entry["from"], entry["to"]) for entry in entries} == {
        ("alpha", "beta"),
        ("gamma", "delta"),
    }
    assert all(entry["bridge_kind"] == "relation" for entry in entries)


async def test_export_to_json_skips_write_when_only_non_relation_bridges_change(
    engine, sync_paths: Path
):
    await engine.store(
        project="__bridges__",
        content="BRIDGE: alpha → beta | Patrón: shared-cache | Nota: relation",
        fact_type="bridge",
        tags=["alpha", "beta", "shared-cache"],
        source="sync-agent-memory",
        meta={
            "date": "2026-04-04T10:00:00Z",
            "from": "alpha",
            "to": "beta",
            "pattern": "shared-cache",
            "note": "relation",
        },
    )

    first_result = await export_to_json(engine)
    first_content = (sync_paths / "bridges.jsonl").read_text(encoding="utf-8")

    assert first_result.files_written >= 1

    await engine.store(
        project="__bridges__",
        content="BRIDGE: repo → issue | Patrón: github | Nota: external",
        fact_type="bridge",
        tags=["repo", "issue", "github"],
        source="bridge:github",
        meta={
            "date": "2026-04-04T12:00:00Z",
            "from": "repo",
            "to": "issue",
            "pattern": "github",
            "note": "external",
            "github_key": "repo#1",
        },
    )

    second_result = await export_to_json(engine)
    second_content = (sync_paths / "bridges.jsonl").read_text(encoding="utf-8")

    assert second_result.files_written == 0
    assert second_content == first_content
