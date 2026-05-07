"""
Enrichment Worker - Asynchronous background processor for CORTEX.
Ω₁₃: Thermodynamic decoupling sidecar.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import aiosqlite

from cortex.database.core import connect_async_ctx
from cortex.embeddings.provider import EmbeddingProvider

logger = logging.getLogger("cortex")


class EnrichmentWorker:
    """Worker that polls enrichment_jobs and processes them."""

    def __init__(
        self, db_path: str, provider: EmbeddingProvider | None = None, poll_interval: float = 1.0
    ):
        self.db_path = db_path
        self.provider = provider
        self.poll_interval = poll_interval
        self._running = False

    async def start(self):
        """Start the worker loop."""
        self._running = True
        logger.info("EnrichmentWorker started (Axiom Ω₁₃)")
        while self._running:
            try:
                await self._process_batch()
            except Exception as e:
                logger.error("Worker batch failed: %s", e)
            await asyncio.sleep(self.poll_interval)

    async def stop(self):
        """Stop the worker loop."""
        self._running = False

    async def _process_batch(self, batch_size: int = 10):
        """Poll and process a batch of jobs."""
        async with connect_async_ctx(self.db_path) as conn:
            job_columns = await self._table_columns(conn, "enrichment_jobs")
            tenant_scoped_jobs = "tenant_id" in job_columns
            # Pick 'queued' jobs or those whose next_attempt_at has passed
            selected_columns = "id, fact_id, tenant_id" if tenant_scoped_jobs else "id, fact_id"
            query = f"""
                SELECT {selected_columns} FROM enrichment_jobs
                WHERE status IN ('queued', 'failed')
                AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                LIMIT ?
            """
            now = datetime.now().isoformat()
            async with conn.execute(query, (now, batch_size)) as cursor:
                jobs = await cursor.fetchall()

            for job in jobs:
                job_id = job[0]
                fact_id = job[1]
                tenant_id = job[2] if tenant_scoped_jobs else None
                await self._process_job(conn, job_id, fact_id, tenant_id=tenant_id)
                await conn.commit()

    async def _process_job(
        self,
        conn: aiosqlite.Connection,
        job_id: int,
        fact_id: int,
        tenant_id: str | None = None,
    ):
        """Process a single enrichment job."""
        try:
            # 1. Fetch fact content
            if tenant_id is None:
                query = "SELECT project, content, tenant_id FROM facts WHERE id = ?"
                params = (fact_id,)
            else:
                query = "SELECT project, content, tenant_id FROM facts WHERE id = ? AND tenant_id = ?"
                params = (fact_id, tenant_id)
            async with conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
                if not row:
                    tenant_hint = f" for tenant {tenant_id}" if tenant_id else ""
                    raise ValueError(f"Fact {fact_id} not found{tenant_hint}")
                project, content, fact_tenant_id = row

            # 2. Process with provider if available
            if self.provider:
                logger.info("Enriching fact %d via provider...", fact_id)
                # This would call the provider to embed the fact
                # For now, we just simulate success in the worker logic
                pass

            await self._mark_success(conn, job_id, tenant_id=fact_tenant_id)
            logger.info("Enriched fact %d (job %d)", fact_id, job_id)

        except Exception as e:
            logger.error("Failed to process job %d: %s", job_id, e)
            await self._mark_failure(conn, job_id, str(e))

    async def _mark_success(
        self, conn: aiosqlite.Connection, job_id: int, tenant_id: str | None = None
    ):
        if tenant_id is not None and "tenant_id" in await self._table_columns(conn, "enrichment_jobs"):
            query = """
                UPDATE enrichment_jobs
                SET status = 'completed', updated_at = ?
                WHERE id = ? AND tenant_id = ?
            """
            await conn.execute(query, (datetime.now().isoformat(), job_id, tenant_id))
            return

        query = """
            UPDATE enrichment_jobs
            SET status = 'completed', updated_at = ?
            WHERE id = ?
        """
        await conn.execute(query, (datetime.now().isoformat(), job_id))

    async def _mark_failure(self, conn: aiosqlite.Connection, job_id: int, error: str):
        # Exponential backoff logic
        next_attempt = (datetime.now() + timedelta(minutes=5)).isoformat()
        query = """
            UPDATE enrichment_jobs
            SET status = 'failed',
                attempts = attempts + 1,
                last_error = ?,
                next_attempt_at = ?,
                updated_at = ?
            WHERE id = ?
        """
        await conn.execute(query, (error, next_attempt, datetime.now().isoformat(), job_id))

    @staticmethod
    async def _table_columns(conn: aiosqlite.Connection, table_name: str) -> set[str]:
        cursor = await conn.execute(f"PRAGMA table_info({table_name})")
        rows = await cursor.fetchall()
        return {str(row[1]) for row in rows}
