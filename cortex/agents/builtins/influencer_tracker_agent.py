"""influencer_tracker_agent.py — InfluencerTrackerAgent

Sovereign contact-tracking agent for influencer/streamer outreach.

Responsibilities:
  - Bootstrap SQLite table from influencers_contacts.csv (idempotent seed)
  - CRUD for influencer contact records: upsert, query, delete, list
  - Confidence-tier filtering (C5-REAL | C4 | any)
  - Reply via MessageBus TASK_RESULT

Supported ops (TASK_REQUEST payload.op):
  "seed"   — load CSV into DB (idempotent)
  "upsert" — insert or update a single record
  "get"    — fetch by name (exact, case-insensitive)
  "list"   — list all records, optional confidence filter
  "delete" — remove by name
  "stats"  — count by confidence tier

CORTEX Invariants enforced:
  - No bare except — specific exception types only
  - No bare print — logging module only
  - Type hints on all public surfaces
  - No float for scoring — confidence stored as TEXT
  - Async-safe: aiosqlite for DB, asyncio.sleep not time.sleep
"""

from __future__ import annotations

import asyncio
import csv
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import aiosqlite

from cortex.agents.base import BaseAgent
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

_DEFAULT_CSV = Path(__file__).parents[4] / "influencers_contacts.csv"
_VALID_CONFIDENCE = frozenset({"C5-REAL", "C4", "C3", "C2", "C1"})
_SUPPORTED_OPS = frozenset({"seed", "upsert", "get", "list", "delete", "stats"})

# Basic email format check — deterministic guard, no stochastic guessing
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── Domain model ───────────────────────────────────────────────────────────────


@dataclass
class InfluencerContact:
    """Immutable value object for a single influencer contact record."""

    name: str
    email: str
    source_type: str
    confidence: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)  # type: ignore[return-value]


# ── Repository ─────────────────────────────────────────────────────────────────


class InfluencerRepository:
    """Async SQLite repository — all writes are idempotent."""

    _DDL = """
    CREATE TABLE IF NOT EXISTS influencer_contacts (
        name        TEXT PRIMARY KEY COLLATE NOCASE,
        email       TEXT NOT NULL,
        source_type TEXT NOT NULL,
        confidence  TEXT NOT NULL CHECK(confidence IN ('C5-REAL','C4','C3','C2','C1'))
    )
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)

    async def initialize(self) -> None:
        """Create schema if not present."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(self._DDL)
            await db.commit()
        logger.info("InfluencerRepository initialized at %s", self._db_path)

    async def upsert(self, contact: InfluencerContact) -> None:
        """Insert or replace a contact record."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO influencer_contacts (name, email, source_type, confidence)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    email       = excluded.email,
                    source_type = excluded.source_type,
                    confidence  = excluded.confidence
                """,
                (contact.name, contact.email, contact.source_type, contact.confidence),
            )
            await db.commit()

    async def get(self, name: str) -> InfluencerContact | None:
        """Fetch by name (case-insensitive). Returns None if not found."""
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT name, email, source_type, confidence "
                "FROM influencer_contacts WHERE name = ? COLLATE NOCASE",
                (name,),
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            return None
        return InfluencerContact(
            name=row["name"],
            email=row["email"],
            source_type=row["source_type"],
            confidence=row["confidence"],
        )

    async def list_all(self, confidence: str | None = None) -> list[InfluencerContact]:
        """Return all contacts, optionally filtered by confidence tier."""
        sql = "SELECT name, email, source_type, confidence FROM influencer_contacts"
        params: tuple[str, ...] = ()
        if confidence is not None:
            sql += " WHERE confidence = ?"
            params = (confidence,)
        sql += " ORDER BY name COLLATE NOCASE"

        contacts: list[InfluencerContact] = []
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                async for row in cursor:
                    contacts.append(
                        InfluencerContact(
                            name=row["name"],
                            email=row["email"],
                            source_type=row["source_type"],
                            confidence=row["confidence"],
                        )
                    )
        return contacts

    async def delete(self, name: str) -> bool:
        """Delete by name. Returns True if a row was deleted."""
        async with aiosqlite.connect(self._db_path) as db:
            cursor = await db.execute(
                "DELETE FROM influencer_contacts WHERE name = ? COLLATE NOCASE",
                (name,),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def stats(self) -> dict[str, int]:
        """Count records grouped by confidence tier."""
        result: dict[str, int] = {}
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT confidence, COUNT(*) AS cnt "
                "FROM influencer_contacts GROUP BY confidence ORDER BY confidence"
            ) as cursor:
                async for row in cursor:
                    result[row[0]] = row[1]
        return result

    async def seed_from_csv(self, csv_path: Path) -> int:
        """Idempotent seed from CSV. Returns number of rows upserted."""
        count = 0
        with csv_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for raw in reader:
                name = (raw.get("name") or "").strip()
                email = (raw.get("email") or "").strip()
                source_type = (raw.get("source_type") or "unknown").strip()
                confidence = (raw.get("confidence") or "C3").strip()

                if not name or not email:
                    logger.warning("Skipping row with missing name/email: %s", raw)
                    continue
                if not _EMAIL_RE.match(email):
                    logger.warning("Skipping row with invalid email format: %s", email)
                    continue
                if confidence not in _VALID_CONFIDENCE:
                    logger.warning(
                        "Unknown confidence %r for %s — defaulting to C3", confidence, name
                    )
                    confidence = "C3"

                contact = InfluencerContact(
                    name=name,
                    email=email,
                    source_type=source_type,
                    confidence=confidence,
                )
                await self.upsert(contact)
                count += 1

        logger.info("Seeded %d influencer contacts from %s", count, csv_path)
        return count


# ── Agent ──────────────────────────────────────────────────────────────────────


class InfluencerTrackerAgent(BaseAgent):
    """CORTEX agent — manages influencer contact tracking with SQLite persistence.

    Reactive: responds to TASK_REQUEST messages on the bus.
    Does NOT tick autonomously — pure reactive model.

    Args:
        manifest:    Agent identity and policy contract.
        bus:         CORTEX MessageBus instance.
        tool_registry: Optional tool registry.
        db_path:     SQLite database file path.
        csv_path:    Optional path to seed CSV (defaults to influencers_contacts.csv).
        auto_seed:   If True, seeds from csv_path on on_start() if CSV exists.
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: MessageBus,
        tool_registry: ToolRegistry | None = None,
        *,
        db_path: str | Path = "influencers.db",
        csv_path: Path | None = None,
        auto_seed: bool = True,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self._repo = InfluencerRepository(db_path)
        self._csv_path: Path = csv_path or _DEFAULT_CSV
        self._auto_seed = auto_seed

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def on_start(self) -> None:
        await self._repo.initialize()
        if self._auto_seed and self._csv_path.exists():
            count = await self._repo.seed_from_csv(self._csv_path)
            logger.info("[%s] Auto-seeded %d contacts", self.agent_id, count)
        elif self._auto_seed:
            logger.warning(
                "[%s] CSV not found at %s — skipping auto-seed",
                self.agent_id,
                self._csv_path,
            )

    # ── Message handler ──────────────────────────────────────────────────────

    async def handle_message(self, message: AgentMessage) -> None:
        if message.kind != MessageKind.TASK_REQUEST:
            return

        payload: dict[str, Any] = message.payload or {}
        op: str = payload.get("op", "")

        if op not in _SUPPORTED_OPS:
            await self._reply(
                message,
                {"error": f"unsupported op: {op!r}", "supported": sorted(_SUPPORTED_OPS)},
            )
            return

        try:
            result = await self._dispatch(op, payload)
            await self._reply(message, {"op": op, "result": result})
        except (ValueError, KeyError) as exc:
            logger.warning("[%s] op=%s validation error: %s", self.agent_id, op, exc)
            await self._reply(message, {"op": op, "error": str(exc)})
        except aiosqlite.Error as exc:
            logger.exception("[%s] op=%s DB error", self.agent_id, op)
            await self._reply(message, {"op": op, "error": f"db_error: {exc}"})

    async def tick(self) -> None:
        """Reactive agent — no autonomous tick needed."""
        await asyncio.sleep(0)

    # ── Op dispatch ───────────────────────────────────────────────────────────

    async def _dispatch(self, op: str, payload: dict[str, Any]) -> Any:
        if op == "seed":
            csv_path = Path(payload.get("csv_path", str(self._csv_path)))
            if not csv_path.exists():
                raise ValueError(f"CSV not found: {csv_path}")
            count = await self._repo.seed_from_csv(csv_path)
            return {"seeded": count}

        if op == "upsert":
            contact = self._parse_contact(payload)
            await self._repo.upsert(contact)
            return {"upserted": contact.name}

        if op == "get":
            name = payload.get("name", "").strip()
            if not name:
                raise ValueError("'name' is required for get op")
            contact = await self._repo.get(name)
            if contact is None:
                return {"found": False, "name": name}
            return {"found": True, "contact": contact.as_dict()}

        if op == "list":
            confidence = payload.get("confidence")  # optional filter
            if confidence is not None and confidence not in _VALID_CONFIDENCE:
                raise ValueError(f"invalid confidence: {confidence!r}")
            contacts = await self._repo.list_all(confidence=confidence)
            return {"count": len(contacts), "contacts": [c.as_dict() for c in contacts]}

        if op == "delete":
            name = payload.get("name", "").strip()
            if not name:
                raise ValueError("'name' is required for delete op")
            deleted = await self._repo.delete(name)
            return {"deleted": deleted, "name": name}

        if op == "stats":
            stats = await self._repo.stats()
            total = sum(stats.values())
            return {"total": total, "by_confidence": stats}

        raise ValueError(f"unhandled op: {op!r}")  # safety net

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_contact(payload: dict[str, Any]) -> InfluencerContact:
        """Validate and parse a contact from raw payload dict."""
        name = (payload.get("name") or "").strip()
        email = (payload.get("email") or "").strip()
        source_type = (payload.get("source_type") or "").strip()
        confidence = (payload.get("confidence") or "C3").strip()

        if not name:
            raise ValueError("'name' is required")
        if not email or not _EMAIL_RE.match(email):
            raise ValueError(f"invalid email: {email!r}")
        if not source_type:
            raise ValueError("'source_type' is required")
        if confidence not in _VALID_CONFIDENCE:
            raise ValueError(
                f"invalid confidence: {confidence!r}. Must be one of {_VALID_CONFIDENCE}"
            )

        return InfluencerContact(
            name=name, email=email, source_type=source_type, confidence=confidence
        )

    async def _reply(self, source: AgentMessage, payload: dict[str, Any]) -> None:
        reply = new_message(
            sender=self.manifest.agent_id,
            recipient=source.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=source.message_id,
        )
        await self.bus.send(reply)
