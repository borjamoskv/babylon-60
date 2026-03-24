from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import aiosqlite
import pytest

from cortex.crypto import get_default_encrypter

FACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    project TEXT NOT NULL,
    content TEXT NOT NULL,
    fact_type TEXT NOT NULL DEFAULT 'knowledge',
    confidence TEXT DEFAULT 'C3',
    hash TEXT,
    valid_until TEXT,
    is_quarantined INTEGER DEFAULT 0,
    is_tombstoned INTEGER DEFAULT 0,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _load_bridge_guard():
    root = Path(__file__).resolve().parents[2]
    spec = spec_from_file_location("issue6_bridge_guard", root / "cortex/engine/bridge_guard.py")
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules["issue6_bridge_guard"] = module
    spec.loader.exec_module(module)
    return module.BridgeGuard


@pytest.mark.asyncio
async def test_bridge_audit_decrypts_or_skips_safely() -> None:
    BridgeGuard = _load_bridge_guard()

    conn = await aiosqlite.connect(":memory:")
    await conn.executescript(FACTS_SCHEMA)

    tenant_id = "tenant-a"
    enc = get_default_encrypter()
    valid_bridge_content = enc.encrypt_str(
        "Pattern from proj-source -> proj-target. Adaptation: reuse safely.",
        tenant_id=tenant_id,
    )

    try:
        await conn.executemany(
            "INSERT INTO facts (tenant_id, project, content, fact_type, is_quarantined) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    tenant_id,
                    "proj-source",
                    "Source project fact that later becomes quarantined.",
                    "knowledge",
                    1,
                ),
                (tenant_id, "proj-target", valid_bridge_content, "bridge", 0),
                (tenant_id, "proj-target-2", "v6_aesgcm:not-valid-base64", "bridge", 0),
            ],
        )
        await conn.commit()

        results = await BridgeGuard.audit_bridges(conn, tenant_id=tenant_id)
        by_id = {row["fact_id"]: row for row in results}

        valid_bridge = by_id[2]
        assert valid_bridge["skipped"] is False
        assert valid_bridge["source_project"] == "proj-source"
        assert valid_bridge["allowed"] is False
        assert "Bridge blocked" in valid_bridge["reason"]
        assert valid_bridge["quarantine_ratio"] == 1.0

        skipped_bridge = by_id[3]
        assert skipped_bridge["skipped"] is True
        assert skipped_bridge["source_project"] is None
        assert skipped_bridge["allowed"] is False
        assert skipped_bridge["reason"] == (
            "Bridge audit skipped: content could not be decrypted safely."
        )
        assert skipped_bridge["quarantine_ratio"] == 0.0
    finally:
        await conn.close()
