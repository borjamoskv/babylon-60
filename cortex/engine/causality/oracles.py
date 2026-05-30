"""Oracle interfaces to interpret causal signals."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiosqlite

from cortex.database.core import connect
from cortex.extensions.signals.bus import AsyncSignalBus, SignalBus

logger = logging.getLogger(__name__)


class AsyncCausalOracle:
    """Interprets the Signal Bus to find the parent of a fact asynchronously."""

    @staticmethod
    async def find_parent_signal(
        conn: aiosqlite.Connection,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> int | None:
        """Finds the ID of the parent signal event.

        Args:
            conn: The SQLite database connection.
            tenant_id: Scope of the database query.
            project: Optional project string for filtering.

        Returns:
            The signal ID if found, otherwise None.
        """
        try:
            bus = AsyncSignalBus(conn)
            recent = await bus.history(tenant_id=tenant_id, project=project, limit=5)
            for sig in recent:
                if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                    return sig.id
        except Exception as e:  # noqa: BLE001
            logger.debug("Async causal lookup failed: %s", e)
        return None


class CausalOracle:
    """Interprets the Signal Bus to find the parent of a fact (sync)."""

    @staticmethod
    def find_parent_signal(
        db_path: str,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> int | None:
        """Finds the ID of the parent signal event.

        Args:
            db_path: Path to the database.
            tenant_id: Scope of the database query.
            project: Optional project string for filtering.

        Returns:
            The signal ID if found, otherwise None.
        """
        try:
            with connect(db_path) as conn:
                bus = SignalBus(conn)
                recent = bus.history(tenant_id=tenant_id, project=project, limit=5)
                for sig in recent:
                    if sig.event_type in ("plan:done", "task:start", "apotheosis:heal"):
                        return sig.id
        except Exception as e:  # noqa: BLE001
            logger.debug("Sync causal lookup failed: %s", e)
        return None


def link_causality(
    meta: dict[str, Any] | None,
    signal_id: int | None,
) -> dict[str, Any]:
    """Attach causal metadata to a fact's meta dictionary.

    Args:
        meta: The existing metadata dictionary.
        signal_id: The ID of the causal parent signal.

    Returns:
        The updated metadata dictionary.
    """
    m = meta or {}
    if signal_id:
        m["causal_parent"] = signal_id
        m["axiomatic_integrity"] = "Ω₁"
    return m


def rowless_json(data: dict[str, Any]) -> str:
    """Helper to dump JSON strings predictably.

    Args:
        data: The dictionary to encode.

    Returns:
        The JSON string.
    """
    return json.dumps(data)
