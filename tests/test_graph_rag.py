import os

import pytest

from cortex.memory.graph_store import GraphStore


@pytest.fixture
async def graph_store(tmp_path):
    db_path = str(tmp_path / "test_graph.db")
    store = GraphStore(db_path=db_path)
    await store.initialize()
    yield store
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.mark.asyncio
async def test_graph_store_nodes_and_edges(graph_store):
    """Test fundamental CRUD for GraphRAG nodes and edges."""
    tenant = "tenant_test"
    await graph_store.add_node("n1", tenant, "Company", {"name": "CorpA"})
    await graph_store.add_node("n2", tenant, "Sector", {"name": "AI"})
    
    await graph_store.add_edge("e1", tenant, "n1", "n2", "OPERATES_IN", {"weight": 1.0})
    
    # Verify via multi-hop from n1
    results = await graph_store.multi_hop_query(tenant, "n1", max_depth=1)
    # result should contain n1 and n2
    assert len(results) == 2
    paths = [r["path"] for r in results]
    assert "n1->[OPERATES_IN]->n2" in paths

@pytest.mark.asyncio
async def test_graph_store_multi_hop_reasoning(graph_store):
    """Test 3-hop traversal to prevent LLM hallucination on causal chains."""
    tenant = "tenant_swarm"
    
    # A -> B -> C -> D
    await graph_store.add_node("A", tenant, "Event")
    await graph_store.add_node("B", tenant, "Error")
    await graph_store.add_node("C", tenant, "RootCause")
    await graph_store.add_node("D", tenant, "Resolution")
    
    await graph_store.add_edge("e1", tenant, "A", "B", "TRIGGERED")
    await graph_store.add_edge("e2", tenant, "B", "C", "DUE_TO")
    await graph_store.add_edge("e3", tenant, "C", "D", "FIXED_BY")
    
    # Query from A to depth 3 should find D
    results = await graph_store.multi_hop_query(tenant, "A", max_depth=3)
    
    assert len(results) == 4 # A (0), B (1), C (2), D (3)
    
    # Path of the final hop should trace the entire causal chain
    final_path = next(r["path"] for r in results if r["node_id"] == "D")
    expected_path = "A->[TRIGGERED]->B->[DUE_TO]->C->[FIXED_BY]->D"
    assert final_path == expected_path
