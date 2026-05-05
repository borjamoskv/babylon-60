from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cortex.ledger.models import LedgerEvent


class ReplayProtectionError(ValueError):
    """Raised when strict ledger replay or freshness checks fail."""


@dataclass(frozen=True)
class FreshnessPolicy:
    max_age_seconds: int = 300
    max_future_skew_seconds: int = 60


@dataclass(frozen=True)
class ReplayProtectionPolicy:
    freshness: FreshnessPolicy = FreshnessPolicy()
    now: Callable[[], datetime] | None = None

    def validate_freshness(self, event: LedgerEvent) -> None:
        origin = event.origin
        if origin is None:
            raise ReplayProtectionError("origin_required_for_replay_protection")
        signed_at = _parse_utc(origin.signed_at)
        now = self._now()
        if signed_at < now - timedelta(seconds=self.freshness.max_age_seconds):
            raise ReplayProtectionError("origin_signature_stale")
        if signed_at > now + timedelta(seconds=self.freshness.max_future_skew_seconds):
            raise ReplayProtectionError("origin_signature_from_future")

    def is_idempotent_retry(self, conn: sqlite3.Connection, event: LedgerEvent) -> bool:
        origin = _require_origin(event)
        tenant_id = _tenant_id(event)
        rows = conn.execute(
            """
            SELECT event_id, nonce, origin_signature
            FROM ledger_origin_replay
            WHERE tenant_id = ?
              AND (
                (actor_id = ? AND key_id = ? AND nonce = ?)
                OR event_id = ?
              )
            """,
            (tenant_id, origin.actor_id, origin.key_id, origin.nonce, event.event_id),
        ).fetchall()

        for row in rows:
            same_signed_event = (
                row["event_id"] == event.event_id
                and row["nonce"] == origin.nonce
                and row["origin_signature"] == origin.signature
            )
            if same_signed_event:
                persisted = conn.execute(
                    "SELECT 1 FROM ledger_events WHERE event_id = ?",
                    (event.event_id,),
                ).fetchone()
                if persisted is not None:
                    return True
                raise ReplayProtectionError("origin_replay_orphan_reservation")
            if row["nonce"] == origin.nonce:
                raise ReplayProtectionError("origin_nonce_replay")
            raise ReplayProtectionError("origin_event_id_replay")

        legacy_event = conn.execute(
            "SELECT 1 FROM ledger_events WHERE event_id = ?",
            (event.event_id,),
        ).fetchone()
        if legacy_event is not None:
            raise ReplayProtectionError("origin_event_id_replay")
        return False

    def reserve(self, conn: sqlite3.Connection, event: LedgerEvent) -> None:
        origin = _require_origin(event)
        if not event.hash:
            raise ReplayProtectionError("origin_replay_requires_event_hash")
        tenant_id = _tenant_id(event)
        try:
            conn.execute(
                """
                INSERT INTO ledger_origin_replay (
                    tenant_id,
                    actor_id,
                    key_id,
                    nonce,
                    event_id,
                    signed_at,
                    origin_signature,
                    event_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    origin.actor_id,
                    origin.key_id,
                    origin.nonce,
                    event.event_id,
                    origin.signed_at,
                    origin.signature,
                    event.hash,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ReplayProtectionError("origin_replay_conflict") from exc

    def _now(self) -> datetime:
        current = self.now() if self.now is not None else datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ReplayProtectionError("freshness_clock_missing_timezone")
        return current


def _require_origin(event: LedgerEvent):
    origin = event.origin
    if origin is None or not origin.signature:
        raise ReplayProtectionError("origin_required_for_replay_protection")
    return origin


def _tenant_id(event: LedgerEvent) -> str:
    tenant_id = event.metadata.get("tenant_id")
    if isinstance(tenant_id, str) and tenant_id:
        return tenant_id
    return "default"


def _parse_utc(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ReplayProtectionError("origin_timestamp_invalid") from exc
    if parsed.tzinfo is None:
        raise ReplayProtectionError("origin_timestamp_missing_timezone")
    return parsed
