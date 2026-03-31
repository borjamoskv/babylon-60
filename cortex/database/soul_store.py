"""CORTEX v5.2 — Sovereign Soul Store (Substrate-Level).

High-level repository for managing the "Self" entity (id=0) in the Ledger.
This provides the persistent memory backbone for the Alma identity.
"""

from __future__ import annotations

import logging
from typing import Any

import aiosqlite

from cortex.engine.mutation_engine import MUTATION_ENGINE

logger = logging.getLogger("cortex.soul_store")


# Reserved entity ID for the Sovereign Self (The Soul)
SELF_ENTITY_ID = 0


class SoulStore:
    """Repository for Sovereign Self (Soul) events in entity_events."""

    async def save_pulse(
        self,
        conn: aiosqlite.Connection,
        *,
        payload: dict[str, Any],
        signer: str = "alma_engine",
        tenant_id: str = "sovereign",
    ) -> str:
        """Persist a soul pulse (snapshot of psychological state)."""
        return await MUTATION_ENGINE.apply(
            conn,
            fact_id=SELF_ENTITY_ID,
            tenant_id=tenant_id,
            event_type="SOUL_PULSE",
            payload=payload,
            signer=signer,
        )

    async def save_genesis(
        self,
        conn: aiosqlite.Connection,
        *,
        payload: dict[str, Any],
        signer: str = "genesis_engine",
        tenant_id: str = "sovereign",
    ) -> str:
        """Persist the initial Soul Genesis event."""
        return await MUTATION_ENGINE.apply(
            conn,
            fact_id=SELF_ENTITY_ID,
            tenant_id=tenant_id,
            event_type="SOUL_GENESIS",
            payload=payload,
            signer=signer,
        )

    async def get_latest_state(
        self,
        conn: aiosqlite.Connection,
    ) -> dict[str, Any]:
        """Reconstruct the latest Soul state by replaying its event log."""
        return await MUTATION_ENGINE.replay_state(conn, SELF_ENTITY_ID)

    async def verify_integrity(
        self,
        conn: aiosqlite.Connection,
    ) -> dict[str, Any]:
        """Perform a cryptographic audit of the Soul's hash chain."""
        return await MUTATION_ENGINE.verify_chain(conn, SELF_ENTITY_ID)


# Singleton instance
SOUL_STORE = SoulStore()
