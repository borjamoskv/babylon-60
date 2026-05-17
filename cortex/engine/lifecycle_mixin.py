"""CORTEX Engine — Lifecycle Mixin.

Handles engine startup, shutdown, identity initialization,
and signer management.  Extracted from CortexEngine to reduce
__init__.py below the 300 LOC architecture threshold.

Critical Path: CRITICAL.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger("cortex.engine.lifecycle")


class LifecycleMixin:
    """Engine lifecycle: start, close, identity, signer."""

    async def start(self) -> None:
        """Ignite the sovereign engine and its optimization layers."""
        await self._init_persist_identity()
        await self.start_optimizer()  # type: ignore[attr-defined]
        await self._persistence.start()  # type: ignore[attr-defined]
        logger.info("🚀 [CORTEX] Sovereign Engine ignited (Ω₀-Ω₆).")

    async def close(self) -> None:
        """Shutdown the engine, optimizer, and database connections."""
        await self.stop_optimizer()  # type: ignore[attr-defined]
        if self._post_commit_tasks:  # type: ignore[attr-defined]
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        *self._post_commit_tasks,  # type: ignore[attr-defined]
                        return_exceptions=True,
                    ),
                    timeout=5.0,
                )
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                logger.debug("Post-commit task drain timed out — forcing close")
            self._post_commit_tasks.clear()  # type: ignore[attr-defined]
        if self._memory_manager:  # type: ignore[attr-defined]
            try:
                await asyncio.wait_for(
                    self._memory_manager.wait_for_background(),  # type: ignore
                    timeout=5.0,
                )
            except (asyncio.TimeoutError, Exception):  # noqa: BLE001
                logger.debug("Memory manager background drain timed out — forcing close")
            self._memory_manager = None  # type: ignore[attr-defined]
        self._memory_l1 = None  # type: ignore[attr-defined]
        self._memory_l3 = None  # type: ignore[attr-defined]
        self._memory_ready = False  # type: ignore[attr-defined]
        if self._persistence:  # type: ignore[attr-defined]
            await self._persistence.stop()  # type: ignore[attr-defined]
        if self._conn:  # type: ignore[attr-defined]
            await self._conn.close()  # type: ignore[attr-defined]
            self._conn = None  # type: ignore[attr-defined]
        # Clean up Wave 6 references
        self.mac_maestro = None  # type: ignore
        self.ledger_writer = None  # type: ignore
        self.enrichment_queue = None  # type: ignore
        self.ledger_store = None  # type: ignore
        self._ledger = None  # type: ignore[attr-defined]

    async def _init_persist_identity(self) -> None:
        """Initialize Persist agent identity (CORTEX v6) for Ledger signatures."""
        from cortex.crypto.identity import IdentityOrchestrator
        from cortex.crypto.vault import Vault
        from cortex.database.core import connect_async_ctx

        vault = Vault()
        orchestrator = IdentityOrchestrator(
            vault,
            str(self._db_path),  # type: ignore[attr-defined]
        )

        agent_name = "Persist_Core"
        agent_id = None

        # Check if exists
        async with connect_async_ctx(
            str(self._db_path),  # type: ignore[attr-defined]
            read_only=True,
        ) as conn:
            async with conn.execute(
                "SELECT id FROM agents WHERE name = ? AND is_active = 1 LIMIT 1",
                (agent_name,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    agent_id = row[0]

        # Create if not exists
        if not agent_id:
            from cortex.database.writer import SqliteWriteWorker

            writer = SqliteWriteWorker(str(self._db_path))  # type: ignore[attr-defined]
            await writer.start()
            try:
                agent_id = await orchestrator.create_agent_identity(
                    agent_name,
                    agent_type="core_system",
                    writer=writer,
                )
            finally:
                await writer.stop()

        self._persist_keypair = await orchestrator.load_agent_identity(agent_id)
        logger.info("🛡️ [CORTEX] Loaded Persist agent identity: %s", agent_id)

    def _get_persist_signer(self) -> Any:
        """Return a sync callback that signs payloads with the Persist identity."""
        from cortex.crypto.keys import ZKSwarmIdentity

        def signer(payload: str) -> str | None:
            keypair = getattr(self, "_persist_keypair", None)
            if not keypair or not keypair.private_key_b64:
                return None
            return ZKSwarmIdentity.sign_payload(payload, keypair.private_key_b64)

        return signer

    async def __aenter__(self) -> Any:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
