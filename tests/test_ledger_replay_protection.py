from __future__ import annotations

import dataclasses
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from cortex.ledger.models import ActionResult, ActionTarget, LedgerEvent
from cortex.ledger.origin import (
    OriginKeyRecord,
    OriginKeyRegistry,
    OriginSignaturePolicy,
    sign_event_origin,
)
from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.replay import ReplayProtectionError, ReplayProtectionPolicy
from cortex.ledger.store import LedgerStore, LedgerStoreError
from cortex.ledger.writer import LedgerWriter

ACTOR_ID = "agent-risk-01"
KEY_ID = "ed25519:agent-risk-01:runtime-001"
SIGNED_AT = "2026-02-03T10:15:30Z"
NOW = datetime(2026, 2, 3, 10, 16, 0, tzinfo=timezone.utc)


def test_replay_policy_reserves_nonce_atomically_with_ledger_event(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)
    event = _signed_event(private_key, nonce="nonce-001")

    event_id = writer.append(event)

    with store.tx() as conn:
        row = conn.execute(
            """
            SELECT event_id, nonce, event_hash
            FROM ledger_origin_replay
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()
    assert row is not None
    assert row["nonce"] == "nonce-001"
    assert isinstance(row["event_hash"], str)


def test_replay_policy_requires_origin_policy(tmp_path: Path) -> None:
    store = LedgerStore(tmp_path / "ledger.db")

    with pytest.raises(ValueError, match="replay_policy_requires_origin_policy"):
        LedgerWriter(
            store,
            EnrichmentQueue(store),
            replay_policy=ReplayProtectionPolicy(now=lambda: NOW),
        )


def test_replay_policy_handles_idempotent_retry_without_duplicate_side_effects(
    tmp_path: Path,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)
    event = _signed_event(private_key, nonce="nonce-001")

    first = writer.append(event)
    second = writer.append(event)

    assert second == first
    assert _row_count(store, "ledger_events") == 1
    assert _row_count(store, "ledger_origin_replay") == 1
    assert _row_count(store, "enrichment_jobs") == 1


def test_replay_policy_rejects_nonce_replay_for_different_event(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)
    writer.append(_signed_event(private_key, nonce="nonce-001"))
    replay = _signed_event(private_key, nonce="nonce-001", event_id="evt-replay-002")

    with pytest.raises(ReplayProtectionError, match="origin_nonce_replay"):
        writer.append(replay)

    assert _row_count(store, "ledger_events") == 1
    assert _row_count(store, "ledger_origin_replay") == 1
    assert _row_count(store, "enrichment_jobs") == 1


def test_replay_policy_rejects_stale_signature_before_persistence(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)
    stale = _signed_event(private_key, nonce="nonce-stale", signed_at="2026-02-03T10:00:00Z")

    with pytest.raises(ReplayProtectionError, match="origin_signature_stale"):
        writer.append(stale)

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "ledger_origin_replay") == 0


def test_replay_policy_rejects_future_signature_before_persistence(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)
    future = _signed_event(private_key, nonce="nonce-future", signed_at="2026-02-03T10:18:00Z")

    with pytest.raises(ReplayProtectionError, match="origin_signature_from_future"):
        writer.append(future)

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "ledger_origin_replay") == 0


def test_replay_reservation_rolls_back_when_ledger_insert_fails(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)
    invalid_event = dataclasses.replace(_event(), tool=cast(str, None))
    signed_invalid = sign_event_origin(
        invalid_event,
        key_id=KEY_ID,
        private_key=private_key,
        signed_at=SIGNED_AT,
        nonce="nonce-rollback",
    )

    with pytest.raises(LedgerStoreError):
        writer.append(signed_invalid)

    assert _row_count(store, "ledger_events") == 0
    assert _row_count(store, "ledger_origin_replay") == 0
    assert _row_count(store, "enrichment_jobs") == 0


def test_concurrent_idempotent_retry_writes_one_event(tmp_path: Path) -> None:
    private_key = Ed25519PrivateKey.generate()
    store, writer = _writer(tmp_path, private_key)
    event = _signed_event(private_key, nonce="nonce-concurrent")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: writer.append(event), range(2)))

    assert results == [event.event_id, event.event_id]
    assert _row_count(store, "ledger_events") == 1
    assert _row_count(store, "ledger_origin_replay") == 1
    assert _row_count(store, "enrichment_jobs") == 1


def _writer(
    tmp_path: Path,
    private_key: Ed25519PrivateKey,
) -> tuple[LedgerStore, LedgerWriter]:
    registry = OriginKeyRegistry(
        [
            OriginKeyRecord.from_public_key(
                key_id=KEY_ID,
                actor_id=ACTOR_ID,
                public_key=private_key.public_key(),
                permissions=["fact.store"],
            )
        ]
    )
    store = LedgerStore(tmp_path / "ledger.db")
    return (
        store,
        LedgerWriter(
            store,
            EnrichmentQueue(store),
            origin_policy=OriginSignaturePolicy.strict_mode(registry),
            replay_policy=ReplayProtectionPolicy(now=lambda: NOW),
        ),
    )


def _signed_event(
    private_key: Ed25519PrivateKey,
    *,
    nonce: str,
    event_id: str = "evt-replay-001",
    signed_at: str = SIGNED_AT,
) -> LedgerEvent:
    return sign_event_origin(
        dataclasses.replace(_event(), event_id=event_id),
        key_id=KEY_ID,
        private_key=private_key,
        signed_at=signed_at,
        nonce=nonce,
    )


def _event() -> LedgerEvent:
    return LedgerEvent.new(
        tool="agent-runtime",
        actor=ACTOR_ID,
        action="fact.store",
        target=ActionTarget(app="CORTEX", identifier="fact:001"),
        result=ActionResult(ok=True, latency_ms=12, verified=True),
        metadata={"project": "cortex-persist", "tenant_id": "tenant-acme"},
    )


def _row_count(store: LedgerStore, table_name: str) -> int:
    if table_name not in {"ledger_events", "ledger_origin_replay", "enrichment_jobs"}:
        raise ValueError(f"unsupported table: {table_name}")
    with store.tx() as conn:
        row = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    return int(row["count"])
