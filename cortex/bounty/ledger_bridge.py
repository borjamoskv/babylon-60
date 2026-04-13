"""
Cortex-Persist Bounty Ledger Bridge
====================================
Seals confirmed bug bounty findings as immutable, cryptographically-chained
events in the EventLedgerL3 (cortex.db SQLite WAL).

Usage (from Sigma-Hunter or any external consumer):

    from cortex.bounty.ledger_bridge import seal_finding

    event_id = await seal_finding(
        finding={
            "vector_id": "SKY-Σ1-DUST",
            "protocol": "sky",
            "confidence": "C5-Deterministic",
            "finding": "Integer truncation traps dust permanently in SwapperCalleePsm",
            "seal": "f440610c7d57b75b",
        },
        session_id="legion-10k-2026-04-13",
    )
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.memory.ledger import EventLedgerL3
from cortex.memory.models import MemoryEvent, next_id

logger = logging.getLogger("cortex.bounty.ledger_bridge")

# Default DB path — overridable via CORTEX_DB_PATH env var or constructor arg
_DEFAULT_DB = Path("~/.cortex/cortex.db").expanduser()
BOUNTY_TENANT = "sigma-hunter"


class BountyLedgerBridge:
    """
    High-level interface for sealing bug bounty findings into the Cortex L3 ledger.

    Each confirmed finding is appended as an immutable MemoryEvent with:
      - role="bounty_finding"
      - tenant_id="sigma-hunter"
      - SHA-3-256 chained signature (prev_hash → signature)
      - metadata: vector_id, protocol, confidence, swarm_seal

    After every append the full chain is verified for tamper evidence.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def seal(self, finding: dict[str, Any], session_id: str | None = None) -> str:
        """
        Seal a confirmed finding into the ledger.

        Args:
            finding: Dict with at minimum: vector_id, protocol, confidence, finding, seal
            session_id: Optional session identifier (e.g. "legion-10k-2026-04-13")

        Returns:
            event_id (UUID str) of the sealed event.

        Raises:
            RuntimeError: If chain integrity is violated after append.
        """
        session_id = session_id or f"bounty-{datetime.now(timezone.utc).strftime('%Y%m%d')}"  # noqa: TID251

        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL")
            ledger = EventLedgerL3(conn)
            await ledger.ensure_table()

            event = MemoryEvent(
                event_id=next_id(),
                timestamp=datetime.now(timezone.utc),  # noqa: TID251
                role="bounty_finding",
                content=json.dumps(finding, ensure_ascii=False, sort_keys=True),
                token_count=0,
                session_id=session_id,
                tenant_id=BOUNTY_TENANT,
                metadata={
                    "vector_id": finding.get("vector_id", "unknown"),
                    "protocol": finding.get("protocol", "unknown"),
                    "confidence": finding.get("confidence", "C0-Unknown"),
                    "swarm_seal": finding.get("seal", ""),
                    "bounty_platform": finding.get("bounty_platform", "immunefi"),
                },
            )

            await ledger.append_event(event)
            logger.info(
                "🔏 Finding sealed — vector_id=%s event_id=%s",
                finding.get("vector_id"),
                event.event_id,
            )

            # Verify chain integrity after every append
            audit = await ledger.verify_chain(BOUNTY_TENANT)
            if audit["status"] != "VALID":
                raise RuntimeError(
                    f"LEDGER CHAIN CORRUPT after sealing {finding.get('vector_id')}: "
                    f"{audit['findings']}"
                )

            logger.debug("✓ Chain integrity: VALID (%d events audited)", audit["events_audited"])

        return event.event_id

    async def get_all_findings(self, session_id: str | None = None) -> list[dict[str, Any]]:
        """
        Retrieve all sealed findings for audit or report generation.

        Args:
            session_id: Optional filter by session.

        Returns:
            List of dicts with event_id, timestamp, signature, prev_hash, content, metadata.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL")
            ledger = EventLedgerL3(conn)
            events = await ledger.replay(BOUNTY_TENANT)

        results = []
        for e in events:
            if session_id and e.session_id != session_id:
                continue
            results.append({
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "signature": e.signature,
                "prev_hash": e.prev_hash,
                "content": json.loads(e.content),
                "metadata": e.metadata,
            })
        return results

    async def verify_integrity(self) -> dict[str, Any]:
        """Run a full cryptographic audit of the bounty findings chain."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL")
            ledger = EventLedgerL3(conn)
            return await ledger.verify_chain(BOUNTY_TENANT)

    async def count_findings(self) -> int:
        """Return the total number of sealed findings."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL")
            ledger = EventLedgerL3(conn)
            return await ledger.count(BOUNTY_TENANT)


# ── Module-level convenience functions ──────────────────────────────────────

_default_bridge: BountyLedgerBridge | None = None


def _get_bridge(db_path: Path | str | None = None) -> BountyLedgerBridge:
    global _default_bridge
    if db_path:
        return BountyLedgerBridge(db_path)
    if _default_bridge is None:
        _default_bridge = BountyLedgerBridge()
    return _default_bridge


async def seal_finding(
    finding: dict[str, Any],
    session_id: str | None = None,
    db_path: Path | str | None = None,
) -> str:
    """Module-level shortcut for BountyLedgerBridge.seal()."""
    return await _get_bridge(db_path).seal(finding, session_id)


async def get_sealed_findings(
    session_id: str | None = None,
    db_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Module-level shortcut for BountyLedgerBridge.get_all_findings()."""
    return await _get_bridge(db_path).get_all_findings(session_id)
