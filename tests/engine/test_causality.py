"""Unit tests for Causal Graph and Taint Propagation — cortex/engine/causality.py."""

import json
import pytest
import aiosqlite
from cortex.engine.causality import AsyncCausalGraph, TaintStatus, Confidence

@pytest.fixture
async def db_conn():
    conn = await aiosqlite.connect(":memory:")
    yield conn
    await conn.close()

@pytest.fixture
async def setup_facts(db_conn):
    # Setup minimal facts table
    await db_conn.execute("""
        CREATE TABLE facts (
            id INTEGER PRIMARY KEY,
            confidence TEXT,
            metadata TEXT,
            tenant_id TEXT DEFAULT 'default'
        )
    """)
    await db_conn.commit()

@pytest.mark.asyncio
async def test_causal_graph_table_init(db_conn):
    """Test AsyncCausalGraph table creation."""
    graph = AsyncCausalGraph(db_conn)
    await graph.ensure_table()

    # Verify table exists
    async with db_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='causal_edges'") as cursor:
        row = await cursor.fetchone()
        assert row is not None

@pytest.mark.asyncio
async def test_record_edge(db_conn):
    """Test recording causal edges."""
    graph = AsyncCausalGraph(db_conn)
    await graph.ensure_table()

    await graph.record_edge(fact_id=2, parent_id=1, edge_type="derived_from")

    async with db_conn.execute("SELECT fact_id, parent_id, edge_type FROM causal_edges") as cursor:
        row = await cursor.fetchone()
        assert row == (2, 1, "derived_from")

@pytest.mark.asyncio
async def test_calculate_blast_radius(db_conn):
    """Test calculation of descendant count."""
    graph = AsyncCausalGraph(db_conn)
    await graph.ensure_table()

    # Graph: 1 -> 2, 1 -> 3, 2 -> 4
    edges = [(2, 1), (3, 1), (4, 2)]
    for child, parent in edges:
        await graph.record_edge(fact_id=child, parent_id=parent)

    radius = await graph.calculate_blast_radius(1, "default")
    assert radius == 3 # 2, 3, 4 are descendants

    radius2 = await graph.calculate_blast_radius(2, "default")
    assert radius2 == 1 # 4 is descendant

@pytest.mark.asyncio
async def test_propagate_taint_basic(db_conn, setup_facts):
    """Test basic taint propagation in a chain."""
    graph = AsyncCausalGraph(db_conn)
    await graph.ensure_table()

    # 1 -> 2 -> 3
    await db_conn.execute("INSERT INTO facts (id, confidence, metadata) VALUES (1, 'C5', '{}')")
    await db_conn.execute("INSERT INTO facts (id, confidence, metadata) VALUES (2, 'C5', '{}')")
    await db_conn.execute("INSERT INTO facts (id, confidence, metadata) VALUES (3, 'C5', '{}')")

    await graph.record_edge(2, 1)
    await graph.record_edge(3, 2)
    await db_conn.commit()

    # Invalidate 1
    report = await graph.propagate_taint(1, tenant_id="default", floor_to_c1=True)

    assert report.affected_count == 3
    assert len(report.confidence_changes) == 3

    # Verify DB updates
    async with db_conn.execute("SELECT id, confidence, metadata FROM facts ORDER BY id") as cursor:
        rows = await cursor.fetchall()
        for fid, conf, meta_raw in rows:
            assert conf == "C1"
            meta = json.loads(meta_raw)
            assert meta["taint_status"] in (TaintStatus.TAINTED, TaintStatus.SUSPECT)

@pytest.mark.asyncio
async def test_taint_tenant_isolation(db_conn, setup_facts):
    """Ensure taint does not leak across tenants."""
    graph = AsyncCausalGraph(db_conn)
    await graph.ensure_table()

    # Tenant A: 1 -> 2
    # Tenant B: 3 -> 4
    await db_conn.execute("INSERT INTO facts (id, confidence, tenant_id) VALUES (1, 'C5', 'A')")
    await db_conn.execute("INSERT INTO facts (id, confidence, tenant_id) VALUES (2, 'C5', 'A')")
    await db_conn.execute("INSERT INTO facts (id, confidence, tenant_id) VALUES (3, 'C5', 'B')")
    await db_conn.execute("INSERT INTO facts (id, confidence, tenant_id) VALUES (4, 'C5', 'B')")

    await graph.record_edge(2, 1, tenant_id="A")
    await graph.record_edge(4, 3, tenant_id="B")
    await db_conn.commit()

    # Taint 1 in Tenant A
    await graph.propagate_taint(1, tenant_id="A")

    # Verify Tenant A is tainted
    async with db_conn.execute("SELECT confidence FROM facts WHERE id = 2") as cursor:
        row = await cursor.fetchone()
        assert row[0] == "C1"

    # Verify Tenant B is CLEAN
    async with db_conn.execute("SELECT confidence FROM facts WHERE id = 4") as cursor:
        row = await cursor.fetchone()
        assert row[0] == "C5"
