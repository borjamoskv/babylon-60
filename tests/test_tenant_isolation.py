"""Tests for multi-tenant Row-Level Security (RLS) isolation in CORTEX Engine."""

import os
import tempfile

import pytest

from cortex.engine import CortexEngine
from cortex.extensions.security.tenant import tenant_id_var

@pytest.fixture(autouse=True)
def mock_signals_and_hooks(monkeypatch):
    from cortex.extensions.health.trend import TrendDetector
    monkeypatch.setattr(TrendDetector, "persist_to_db", lambda *args, **kwargs: None)
    monkeypatch.setattr("cortex.extensions.signals.fact_hook.emit_fact_stored", lambda *args, **kwargs: None)



@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
async def engine(temp_db):
    """Engine fixture for memory and search isolation."""
    # Ensure fresh state
    e = CortexEngine(db_path=temp_db, auto_embed=False)
    await e.init_db()
    yield e
    await e.close()


@pytest.mark.asyncio
async def test_tenant_isolation_store_and_recall(engine):
    """Verify that facts stored under one tenant cannot be recalled by another."""

    # Store fact for Alice
    token_alice = tenant_id_var.set("tenant-alice")
    await engine.store(
        content="Alice's secret strategy",
        fact_type="decision",
        project="alpha",
        source="api",
    )
    tenant_id_var.reset(token_alice)

    # Store fact for Bob
    token_bob = tenant_id_var.set("tenant-bob")
    await engine.store(
        content="Bob's secret strategy",
        fact_type="decision",
        project="alpha",
        source="api",
    )
    tenant_id_var.reset(token_bob)

    # Alice queries -> should only see her fact
    token_alice = tenant_id_var.set("tenant-alice")
    facts_alice = await engine.recall(project="alpha")
    assert len(facts_alice) == 1
    assert facts_alice[0]["content"] == "Alice's secret strategy"
    assert facts_alice[0]["tenant_id"] == "tenant-alice"
    tenant_id_var.reset(token_alice)

    # Bob queries -> should only see his fact
    token_bob = tenant_id_var.set("tenant-bob")
    facts_bob = await engine.recall(project="alpha")
    assert len(facts_bob) == 1
    assert facts_bob[0]["content"] == "Bob's secret strategy"
    assert facts_bob[0]["tenant_id"] == "tenant-bob"
    tenant_id_var.reset(token_bob)


@pytest.mark.asyncio
async def test_tenant_isolation_update_and_deprecate(engine):
    """Verify that updating or deprecating cross-tenant facts fails."""

    # Alice stores a fact
    token_alice = tenant_id_var.set("tenant-alice")
    fact_id_alice = await engine.store(
        content="Alice's initial draft", fact_type="knowledge", project="beta", source="api"
    )
    tenant_id_var.reset(token_alice)

    # Bob tries to update Alice's fact
    token_bob = tenant_id_var.set("tenant-bob")
    try:
        updated_id = await engine.update(
            fact_id=fact_id_alice, new_content="Bob hacked this", project="beta"
        )
    except Exception:
        updated_id = None
    assert not updated_id, "Bob should not be able to update Alice's fact"

    # Verify Alice's fact is unchanged
    tenant_id_var.reset(token_bob)

    token_alice = tenant_id_var.set("tenant-alice")
    alice_fact = await engine.get_fact(fact_id_alice)
    assert alice_fact.content == "Alice's initial draft"
    tenant_id_var.reset(token_alice)

@pytest.mark.asyncio
async def test_tenant_isolation_delete_other_tenant_fact_fails(engine):
    """Verify that a tenant cannot deprecate or delete facts belonging to another tenant."""
    # Tenant A stores a fact
    token_a = tenant_id_var.set("tenant-a")
    fact_id_a = await engine.store(
        content="Tenant A confidential data", fact_type="knowledge", project="gamma", source="api"
    )
    tenant_id_var.reset(token_a)

    # Tenant B tries to deprecate Tenant A's fact
    token_b = tenant_id_var.set("tenant-b")
    try:
        deprecated = await engine.deprecate(fact_id_a)
    except Exception:
        deprecated = False
    assert not deprecated, "Tenant B should not be able to deprecate Tenant A's fact"

    # Verify fact still exists and is accessible to Tenant A
    tenant_id_var.reset(token_b)
    token_a = tenant_id_var.set("tenant-a")
    fact_a = await engine.get_fact(fact_id_a)
    assert fact_a is not None
    assert fact_a.content == "Tenant A confidential data"
    tenant_id_var.reset(token_a)


@pytest.mark.asyncio
async def test_tenant_isolation_leakage_on_large_batch_insert(engine):
    """Verify that batch inserts correctly associate all facts with the current active tenant."""
    token_x = tenant_id_var.set("tenant-x")
    batch = [
        {"content": f"Bulk data {i}", "fact_type": "knowledge", "project": "bulk_proj", "source": "api"}
        for i in range(10)
    ]
    fact_ids = await engine.store_many(batch)
    assert len(fact_ids) == 10
    tenant_id_var.reset(token_x)

    # Tenant Y should not see any of the bulk facts
    token_y = tenant_id_var.set("tenant-y")
    facts_y = await engine.recall(project="bulk_proj")
    assert len(facts_y) == 0, "Tenant Y can see Tenant X's batch inserted facts!"
    tenant_id_var.reset(token_y)

    # Tenant X should see all 10
    token_x = tenant_id_var.set("tenant-x")
    facts_x = await engine.recall(project="bulk_proj")
    assert len(facts_x) == 10
    for fact in facts_x:
        assert fact["tenant_id"] == "tenant-x"
    tenant_id_var.reset(token_x)

@pytest.mark.asyncio
async def test_tenant_isolation_purge_force_rejects_other_tenant(engine):
    """Verify that even purge with force=True is isolated to the tenant."""
    # Tenant M stores a fact
    token_m = tenant_id_var.set("tenant-m")
    fact_id_m = await engine.store(
        content="Crucial state M", fact_type="knowledge", project="delta", source="api"
    )
    tenant_id_var.reset(token_m)

    # Tenant N tries to purge Tenant M's fact forcibly
    token_n = tenant_id_var.set("tenant-n")
    try:
        purged = await engine.purge(fact_id_m, force=True)
    except Exception:
        purged = False
    assert not purged, "Tenant N purged Tenant M's fact forcefully"
    tenant_id_var.reset(token_n)

    # Ensure the fact survives
    token_m = tenant_id_var.set("tenant-m")
    fact_m = await engine.get_fact(fact_id_m)
    assert fact_m is not None
    assert fact_m.content == "Crucial state M"
    tenant_id_var.reset(token_m)
