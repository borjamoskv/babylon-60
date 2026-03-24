"""Tests for cortex.engine.bridge_guard.BridgeGuard — tenant isolation.

Uses in-memory SQLite to verify that audit_bridges correctly scopes
queries to the requesting tenant.
"""

from __future__ import annotations

import aiosqlite
import pytest

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


@pytest.fixture
async def conn():
    """In-memory SQLite with facts schema."""
    db = await aiosqlite.connect(":memory:")
    await db.executescript(FACTS_SCHEMA)
    # Seed bridge facts across two tenants
    await db.executemany(
        "INSERT INTO facts (tenant_id, project, content, fact_type) VALUES (?, ?, ?, ?)",
        [
            ("tenant_a", "proj_x", "Pattern from proj_y → proj_x. Adaptation: reuse", "bridge"),
            ("tenant_a", "proj_y", "Pattern from proj_x → proj_y. Adaptation: sync", "bridge"),
            ("tenant_b", "proj_z", "Pattern from proj_w → proj_z. Adaptation: port", "bridge"),
        ],
    )
    await db.commit()
    yield db
    await db.close()


class TestBridgeGuardTenantIsolation:
    async def test_audit_returns_only_own_tenant(self, conn):
        """audit_bridges must not return bridges from other tenants."""
        from cortex.engine.bridge_guard import BridgeGuard

        results_a = await BridgeGuard.audit_bridges(conn, tenant_id="tenant_a")
        results_b = await BridgeGuard.audit_bridges(conn, tenant_id="tenant_b")

        assert len(results_a) == 2, f"Expected 2 bridges for tenant_a, got {len(results_a)}"
        assert len(results_b) == 1, f"Expected 1 bridge for tenant_b, got {len(results_b)}"

        # Verify no cross-contamination
        projects_a = {r["project"] for r in results_a}
        assert "proj_z" not in projects_a, "tenant_a must not see tenant_b bridges"

    async def test_audit_empty_tenant_returns_nothing(self, conn):
        """Unknown tenant should return empty list."""
        from cortex.engine.bridge_guard import BridgeGuard

        results = await BridgeGuard.audit_bridges(conn, tenant_id="ghost_tenant")
        assert results == []

    async def test_quarantine_ratio_scoped_to_tenant(self, conn):
        """Quarantine ratio must be tenant-scoped."""
        from cortex.engine.bridge_guard import BridgeGuard

        # Quarantine one fact in tenant_a
        await conn.execute(
            "UPDATE facts SET is_quarantined = 1 WHERE tenant_id = 'tenant_a' AND project = 'proj_x'"
        )
        await conn.commit()

        ratio_a = await BridgeGuard._quarantine_ratio(conn, "proj_x", "tenant_a")
        ratio_b = await BridgeGuard._quarantine_ratio(conn, "proj_z", "tenant_b")

        assert ratio_a == 1.0, "All proj_x facts in tenant_a are quarantined"
        assert ratio_b == 0.0, "No proj_z facts in tenant_b are quarantined"
