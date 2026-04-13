from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from cortex.ledger.models import ActionResult, ActionTarget, LedgerEvent
from cortex.ledger.queue import EnrichmentQueue
from cortex.ledger.store import LedgerStore, LedgerStoreError
from cortex.ledger.verifier import LedgerVerifier
from cortex.ledger.writer import LedgerWriter


def _make_event(identifier: str) -> LedgerEvent:
    return LedgerEvent.new(
        tool="test",
        actor="tester",
        action="append",
        target=ActionTarget(app="tests", identifier=identifier),
        result=ActionResult(ok=True, latency_ms=1),
        metadata={"project": "tests"},
    )


@pytest.fixture
def ledger_stack(tmp_path: Path) -> tuple[LedgerStore, EnrichmentQueue, LedgerWriter]:
    store = LedgerStore(tmp_path / "ledger.db")
    queue = EnrichmentQueue(store)
    writer = LedgerWriter(store, queue)
    return store, queue, writer


def test_append_persists_event_and_enrichment_job(ledger_stack) -> None:
    store, _, writer = ledger_stack

    event_id = writer.append(_make_event("1"))

    with store.tx() as conn:
        event_row = conn.execute(
            "SELECT event_id, semantic_status FROM ledger_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        job_row = conn.execute(
            "SELECT event_id, status FROM enrichment_jobs WHERE event_id = ?",
            (event_id,),
        ).fetchone()

    assert event_row is not None
    assert event_row["semantic_status"] == "pending"
    assert job_row is not None
    assert job_row["event_id"] == event_id
    assert job_row["status"] == "queued"


def test_append_rolls_back_event_when_enqueue_fails(monkeypatch, ledger_stack) -> None:
    store, queue, writer = ledger_stack

    def _fail_enqueue(_conn, _event_id: str) -> str:
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(queue, "_enqueue_with_conn", _fail_enqueue)

    with pytest.raises(LedgerStoreError, match="queue unavailable"):
        writer.append(_make_event("1"))

    with store.tx() as conn:
        event_count = conn.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]
        job_count = conn.execute("SELECT COUNT(*) FROM enrichment_jobs").fetchone()[0]

    assert event_count == 0
    assert job_count == 0


def test_store_tx_rolls_back_partial_write_on_error(ledger_stack) -> None:
    store, _, _ = ledger_stack

    with pytest.raises(LedgerStoreError, match="boom"):
        with store.tx() as conn:
            conn.execute(
                """
                INSERT INTO ledger_events (
                    event_id, ts, tool, actor, action, payload_json,
                    prev_hash, hash, semantic_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-1",
                    "2026-01-01T00:00:00+00:00",
                    "test",
                    "tester",
                    "append",
                    "{}",
                    "GENESIS",
                    "hash-1",
                    "pending",
                ),
            )
            raise RuntimeError("boom")

    with store.tx() as conn:
        event_count = conn.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]

    assert event_count == 0


def test_store_tx_rejects_ledger_event_without_hash_continuity(ledger_stack) -> None:
    store, _, _ = ledger_stack

    with pytest.raises(LedgerStoreError, match="prev_hash/hash required"):
        with store.tx() as conn:
            conn.execute(
                """
                INSERT INTO ledger_events (
                    event_id, ts, tool, actor, action, payload_json, semantic_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-missing-hash",
                    "2026-01-01T00:00:00+00:00",
                    "test",
                    "tester",
                    "append",
                    "{}",
                    "pending",
                ),
            )


def test_append_preserves_linear_chain_under_concurrency(ledger_stack) -> None:
    store, _, writer = ledger_stack
    verifier = LedgerVerifier(store)

    def _append(i: int) -> str:
        return writer.append(_make_event(str(i)))

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(_append, range(200)))

    assert len(results) == 200
    report = verifier.verify_chain()
    assert report["valid"], report["violations"]

    with store.tx() as conn:
        event_count = conn.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]
        job_count = conn.execute("SELECT COUNT(*) FROM enrichment_jobs").fetchone()[0]

    assert event_count == 200
    assert job_count == 200
