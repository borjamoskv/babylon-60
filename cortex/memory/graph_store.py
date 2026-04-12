"""CORTEX v7 — Ontological Memory Store (Graph RAG).

Enforces epistemological boundaries by structuring facts as Nodes and Edges.
Multi-hop traversal prevents LLM hallucination in complex reasoning paths.
"""

import json
import logging
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class GraphStore:
    """Property Graph over SQLite for deterministic multi-hop reasoning."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def initialize(self) -> None:
        """Build the ontological graph schema. Local-first CORTEX compliant."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    node_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    node_type TEXT,
                    attributes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS graph_edges (
                    edge_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    source_id TEXT,
                    target_id TEXT,
                    relation TEXT,
                    attributes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(source_id) REFERENCES graph_nodes(node_id),
                    FOREIGN KEY(target_id) REFERENCES graph_nodes(node_id)
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_graph_source ON graph_edges(source_id)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_graph_target ON graph_edges(target_id)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_graph_tenant ON graph_nodes(tenant_id)"
            )
            await db.commit()

    async def add_node(
        self,
        node_id: str,
        tenant_id: str,
        node_type: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Upsert a node."""
        attrs = json.dumps(attributes) if attributes else "{}"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO graph_nodes (node_id, tenant_id, node_type, attributes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    node_type=excluded.node_type, attributes=excluded.attributes
                """,
                (node_id, tenant_id, node_type, attrs),
            )
            await db.commit()

    async def add_edge(
        self,
        edge_id: str,
        tenant_id: str,
        source_id: str,
        target_id: str,
        relation: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Add an edge between two nodes."""
        attrs = json.dumps(attributes) if attributes else "{}"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO graph_edges
                    (edge_id, tenant_id, source_id, target_id, relation, attributes)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(edge_id) DO UPDATE SET
                    relation=excluded.relation, attributes=excluded.attributes
                """,
                (edge_id, tenant_id, source_id, target_id, relation, attrs),
            )
            await db.commit()

    async def multi_hop_query(
        self,
        tenant_id: str,
        start_node_id: str,
        max_depth: int = 3,
    ) -> list[dict[str, Any]]:
        """Traverse the graph deterministically via recursive CTE."""
        async with aiosqlite.connect(self.db_path) as db:
            query = """
            WITH RECURSIVE traverse(node_id, path, depth) AS (
                SELECT node_id, node_id, 0
                FROM graph_nodes
                WHERE node_id = ? AND tenant_id = ?

                UNION ALL

                SELECT ge.target_id,
                       t.path || '->[' || ge.relation || ']->' || ge.target_id,
                       t.depth + 1
                FROM graph_edges ge
                JOIN traverse t ON ge.source_id = t.node_id
                WHERE t.depth < ? AND ge.tenant_id = ?
            )
            SELECT t.node_id, t.path, n.node_type, n.attributes
            FROM traverse t
            JOIN graph_nodes n ON t.node_id = n.node_id
            ORDER BY t.depth ASC;
            """
            db.row_factory = aiosqlite.Row
            async with db.execute(
                query, (start_node_id, tenant_id, max_depth, tenant_id)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "node_id": r["node_id"],
                        "path": r["path"],
                        "node_type": r["node_type"],
                        "attributes": (json.loads(r["attributes"]) if r["attributes"] else {}),
                    }
                    for r in rows
                ]
