from __future__ import annotations

import dataclasses


def test_queue_retries_on_provider_failure(tmp_path):
    from cortex.ledger.models import ActionResult, ActionTarget, LedgerEvent
    from cortex.ledger.queue import EnrichmentQueue
    from cortex.ledger.store import LedgerStore

    db = tmp_path / "ledger.db"
    store = LedgerStore(db)
    queue = EnrichmentQueue(store)
    event = LedgerEvent.new(
        tool="mac_maestro",
        actor="agent",
        action="click",
        target=ActionTarget(app="TextEdit"),
        result=ActionResult(ok=True, latency_ms=42),
        metadata={"project": "tests"},
    )
    event = dataclasses.replace(event, event_id="e1")
    event_hash = event.compute_hash("GENESIS")

    with store.tx() as conn:
        conn.execute(
            """
            INSERT INTO ledger_events (
                event_id, ts, tool, actor, action, payload_json,
                prev_hash, hash, semantic_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            ,
            (
                event.event_id,
                event.ts,
                event.tool,
                event.actor,
                event.action,
                event.to_json(),
                "GENESIS",
                event_hash,
                "pending",
            ),
        )

    job_id = queue.enqueue(event.event_id)
    claimed = queue.claim_one()
    assert claimed is not None

    queue.mark_failed(job_id, event.event_id, "provider down", attempts=0)

    with store.tx() as conn:
        row = conn.execute(
            """
            SELECT status, attempts, last_error
            FROM enrichment_jobs
            WHERE job_id=?
            """,
            (job_id,),
        ).fetchone()

    assert row is not None
    assert row["status"] == "retry"
    assert row["attempts"] == 1
    assert "provider down" in row["last_error"]
