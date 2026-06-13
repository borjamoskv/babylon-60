from __future__ import annotations

import json
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from cortex.crypto import get_default_encrypter
from cortex.engine.causality_models import (
    EDGE_TAINTED_BY,
    Confidence,
    TaintReport,
    TaintStatus,
    _downgrade_confidence,
)

logger = logging.getLogger(__name__)

class AsyncCausalGraphTaintMixin:
    # Need to type self properly or rely on duck typing if it's a mixin
    # We'll just define the connection and other required methods that are expected to exist
    conn: aiosqlite.Connection

    async def _metadata_column(self) -> str | None:
        raise NotImplementedError

    async def _fact_columns(self) -> set[str]:
        raise NotImplementedError

    async def propagate_taint(
        self,
        fact_id: int,
        tenant_id: str = "default",
        floor_to_c1: bool = True,
    ) -> TaintReport:
        """Propagates causal taint (Ω₁₃) from a source fact to all descendants."""
        now = datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat()
        meta_col = await self._metadata_column()
        fact_cols = await self._fact_columns()
        has_tenant = "tenant_id" in fact_cols

        descendant_ids = await self._get_descendant_ids(fact_id, tenant_id)

        edges = await self._fetch_edges(list(descendant_ids), tenant_id)
        # Fetch data for descendants and parents
        parent_ids = {p for ps in edges.values() for p in ps}
        nodes_data = await self._fetch_nodes_data(
            list({fact_id} | descendant_ids | parent_ids),
            meta_col,
            has_tenant,
            tenant_id,
        )

        # BFS Propagation
        changes, states = self._process_taint_propagation(
            fact_id, descendant_ids, edges, nodes_data, floor_to_c1, now
        )

        if changes:
            await self._apply_fact_updates(
                changes, nodes_data, meta_col, has_tenant, tenant_id
            )
            await self._record_taint_edges(changes, fact_id, has_tenant, tenant_id)
            await self.conn.commit()

        return TaintReport(
            source_fact_id=fact_id,
            affected_count=len(changes),
            confidence_changes=changes,
        )

    async def _get_descendant_ids(self, fact_id: int, tenant_id: str) -> set[int]:
        """Fetch all transitive descendants of the fact."""
        sql = """
        WITH RECURSIVE descendants AS (
            SELECT fact_id FROM causal_edges
            WHERE parent_id = ? AND tenant_id = ?
            UNION
            SELECT ce.fact_id FROM causal_edges ce
            JOIN descendants d ON ce.parent_id = d.fact_id
            WHERE ce.tenant_id = ?
        )
        SELECT fact_id FROM descendants
        """
        async with self.conn.execute(sql, (fact_id, tenant_id, tenant_id)) as cursor:
            rows = await cursor.fetchall()
            return {int(r[0]) for r in rows}

    async def _fetch_edges(self, node_ids: list[int], tenant_id: str) -> dict[int, list[int]]:
        """Returns {child_id: [parent_ids]} for the given nodes."""
        if not node_ids:
            return {}

        placeholders = ",".join("?" for _ in node_ids)
        sql = f"""
        SELECT fact_id, parent_id FROM causal_edges
        WHERE fact_id IN ({placeholders})
        AND parent_id IS NOT NULL
        AND tenant_id = ?
        """
        params = [*node_ids, tenant_id]

        edges: dict[int, list[int]] = {}
        async with self.conn.execute(sql, params) as cursor:
            async for row in cursor:
                child_id, parent_id = int(row[0]), int(row[1])
                edges.setdefault(child_id, []).append(parent_id)
        return edges

    async def _fetch_nodes_data(
        self,
        node_ids: list[int],
        meta_col: str | None,
        has_tenant: bool,
        tenant_id: str,
    ) -> dict[int, dict[str, Any]]:
        """Fetch confidence and metadata for nodes."""
        nodes_data = {}
        enc = get_default_encrypter()

        chunk_size = 100
        for i in range(0, len(node_ids), chunk_size):
            chunk = node_ids[i : i + chunk_size]
            placeholders = ",".join("?" for _ in chunk)

            cols = "id, confidence"
            if meta_col:
                cols += f", {meta_col}"

            fact_sql = f"SELECT {cols} FROM facts WHERE id IN ({placeholders})"
            params = list(chunk)

            if has_tenant:
                fact_sql += " AND tenant_id = ?"
                params.append(tenant_id)  # pyright: ignore[reportArgumentType]

            async with self.conn.execute(fact_sql, params) as cursor:
                async for row in cursor:
                    fid = int(row[0])
                    conf = row[1] or "C5"
                    raw_meta = row[2] if meta_col and len(row) > 2 else "{}"

                    meta, is_json, is_encrypted = self._parse_metadata(raw_meta, tenant_id, enc)
                    nodes_data[fid] = {
                        "confidence": conf,
                        "metadata": meta,
                        "is_json": is_json,
                        "is_encrypted": is_encrypted,
                        "raw_meta": raw_meta,
                    }
        return nodes_data

    def _parse_metadata(
        self, raw_meta: str, tenant_id: str, enc: Any
    ) -> tuple[dict[str, Any], bool, bool]:
        """Helper to decrypt and parse metadata JSON."""
        if not raw_meta:
            return {}, False, False

        if isinstance(raw_meta, str) and raw_meta.startswith(enc.PREFIX):
            try:
                meta = enc.decrypt_json(raw_meta, tenant_id=tenant_id) or {}
                return meta, True, True
            except (ValueError, TypeError):
                logger.warning("Failed to decrypt metadata")
                return {}, False, False

        try:
            meta = json.loads(raw_meta)
            return meta, True, False
        except (TypeError, json.JSONDecodeError):
            return {"_raw": raw_meta}, False, False

    def _process_taint_propagation(
        self,
        source_id: int,
        descendant_ids: set[int],
        edges: dict[int, list[int]],
        nodes_data: dict[int, dict[str, Any]],
        floor_to_c1: bool,
        timestamp: str,
    ) -> tuple[list[dict[str, Any]], dict[int, TaintStatus]]:
        """BFS traversal to compute new states and confidence levels."""
        node_states: dict[int, TaintStatus] = {source_id: TaintStatus.TAINTED}
        children_map: dict[int, list[int]] = {}
        for child, parents in edges.items():
            for parent in parents:
                children_map.setdefault(parent, []).append(child)

        queue = deque([source_id])
        visited: set[int] = {source_id}
        changes: list[dict[str, Any]] = []

        while queue:
            curr_id = queue.popleft()
            data = nodes_data.get(curr_id)
            if not data:
                continue

            old_conf = data["confidence"]
            new_status = self._derive_node_status(
                curr_id, source_id, edges, nodes_data, node_states
            )
            node_states[curr_id] = new_status

            new_conf = old_conf
            if new_status != TaintStatus.CLEAN:
                new_conf = (
                    Confidence.C1.value if floor_to_c1 else _downgrade_confidence(old_conf, 1)
                )

            if new_conf != old_conf or new_status != TaintStatus.CLEAN:
                if data["is_json"]:
                    data["metadata"].update(
                        {
                            "taint_status": new_status.value,
                            "tainted_by": source_id,
                            "taint_timestamp": timestamp,
                        }
                    )

                changes.append(
                    {
                        "fact_id": curr_id,
                        "old_confidence": old_conf,
                        "new_confidence": new_conf,
                        "status": new_status.value,
                    }
                )

            for child_id in children_map.get(curr_id, []):
                if child_id not in visited and child_id in descendant_ids:
                    visited.add(child_id)
                    queue.append(child_id)

        return changes, node_states

    def _derive_node_status(
        self,
        curr_id: int,
        source_id: int,
        edges: dict[int, list[int]],
        nodes_data: dict[int, dict[str, Any]],
        node_states: dict[int, TaintStatus],
    ) -> TaintStatus:
        """Determines the TaintStatus of a node based on its parents."""
        if curr_id == source_id:
            return TaintStatus.TAINTED

        parents = edges.get(curr_id, [])
        if not parents:
            return TaintStatus.CLEAN

        p_states = []
        for pid in parents:
            if pid in node_states:
                p_states.append(node_states[pid])
            else:
                p_meta = nodes_data.get(pid, {}).get("metadata", {})
                p_status = p_meta.get("taint_status", TaintStatus.CLEAN.value)
                try:
                    p_states.append(TaintStatus(p_status))
                except ValueError:
                    p_states.append(TaintStatus.CLEAN)

        if all(s == TaintStatus.TAINTED for s in p_states):
            return TaintStatus.TAINTED
        if any(s in (TaintStatus.TAINTED, TaintStatus.SUSPECT) for s in p_states):
            return TaintStatus.SUSPECT
        return TaintStatus.CLEAN

    async def _apply_fact_updates(
        self,
        changes: list[dict[str, Any]],
        nodes_data: dict[int, dict[str, Any]],
        meta_col: str | None,
        has_tenant: bool,
        tenant_id: str,
    ) -> None:
        """Execute batch updates to the facts table."""
        fact_updates: list[tuple[Any, ...]] = []
        enc = get_default_encrypter()

        for chg in changes:
            fid = chg["fact_id"]
            data = nodes_data[fid]
            new_conf = chg["new_confidence"]

            if meta_col:
                if data["is_encrypted"]:
                    payload = enc.encrypt_json(data["metadata"], tenant_id=tenant_id)
                elif data["is_json"]:
                    payload = json.dumps(data["metadata"])
                else:
                    payload = data.get("raw_meta", "")
                row = (new_conf, payload, fid)
            else:
                row = (new_conf, fid)

            if has_tenant:
                row = (*row, tenant_id)
            fact_updates.append(row)

        sql = "UPDATE facts SET confidence = ?"
        if meta_col:
            sql += f", {meta_col} = ?"
        sql += " WHERE id = ?"
        if has_tenant:
            sql += " AND tenant_id = ?"

        await self.conn.executemany(sql, fact_updates)

    async def _record_taint_edges(
        self,
        changes: list[dict[str, Any]],
        source_id: int,
        has_tenant: bool,
        tenant_id: str,
    ) -> None:
        """Log causal taint edges for auditability."""
        params = []
        for chg in changes:
            if chg["fact_id"] == source_id:
                continue

            row = [chg["fact_id"], source_id, None, EDGE_TAINTED_BY, None]
            if has_tenant:
                row.append(tenant_id)
            params.append(tuple(row))

        if not params:
            return

        sql = (
            """
        INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project, tenant_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """
            if has_tenant
            else """
        INSERT INTO causal_edges (fact_id, parent_id, signal_id, edge_type, project)
        VALUES (?, ?, ?, ?, ?)
        """
        )
        await self.conn.executemany(sql, params)

    async def calculate_blast_radius(self, fact_id: int, tenant_id: str) -> int:
        sql = """
        WITH RECURSIVE descendants AS (
            SELECT fact_id FROM causal_edges
            WHERE parent_id = ? AND tenant_id = ?
            UNION
            SELECT ce.fact_id FROM causal_edges ce
            JOIN descendants d ON ce.parent_id = d.fact_id
            WHERE ce.tenant_id = ?
        )
        SELECT COUNT(DISTINCT fact_id) FROM descendants
        """
        async with self.conn.execute(sql, (fact_id, tenant_id, tenant_id)) as cursor:
            row = await cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
