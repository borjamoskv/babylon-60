from __future__ import annotations

import importlib
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest

from cortex.engine import store_validation as sv
from cortex.extensions.trust.bayesian import BayesianTrustUpdater, Signal, TrustUpdate


def _make_trust_update(fact_id: int) -> TrustUpdate:
    return TrustUpdate(
        fact_id=fact_id,
        signal="confirm",
        old_confidence="C3",
        new_confidence="C4",
        old_consensus_score=0.5,
        new_consensus_score=0.7,
        alpha=7.0,
        beta=3.0,
        posterior_mean=0.7,
        posterior_variance=0.019091,
        confidence_changed=True,
    )


def _make_event(*, tenant_id: str, session_id: str, content: str):
    from cortex.memory.models import MemoryEvent

    return MemoryEvent(
        role="user",
        content=content,
        token_count=1,
        session_id=session_id,
        tenant_id=tenant_id,
    )


def _make_ledger_components(db_path: Path):
    store, _, writer, verifier = _make_ledger_stack(db_path)
    return store, writer, verifier


def _make_ledger_stack(db_path: Path):
    from cortex.ledger.queue import EnrichmentQueue
    from cortex.ledger.store import LedgerStore
    from cortex.ledger.verifier import LedgerVerifier
    from cortex.ledger.writer import LedgerWriter

    store = LedgerStore(db_path)
    queue = EnrichmentQueue(store)
    writer = LedgerWriter(store, queue)
    verifier = LedgerVerifier(store)
    return store, queue, writer, verifier


def _make_ledger_event(*, action: str = "write"):
    from cortex.ledger.models import ActionResult, ActionTarget, LedgerEvent

    return LedgerEvent.new(
        tool="cli",
        actor="codex",
        action=action,
        target=ActionTarget(app="Test"),
        result=ActionResult(ok=True, latency_ms=10),
        metadata={"project": "safety-net"},
    )


@pytest.mark.asyncio
async def test_memory_event_ledger_falls_back_to_default_tenant_when_security_extension_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    original_import = builtins.__import__

    def broken_import(name: str, *args: object, **kwargs: object):
        if name == "cortex.extensions.security.tenant":
            raise ImportError("tenant extension unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", broken_import)
    sys.modules.pop("cortex.memory.ledger", None)
    ledger_module = importlib.import_module("cortex.memory.ledger")
    EventLedgerL3 = ledger_module.EventLedgerL3

    conn = await aiosqlite.connect(":memory:")
    ledger = EventLedgerL3(conn)
    await ledger.ensure_table()

    await ledger.append_event(_make_event(tenant_id="default", session_id="sess-default", content="d1"))
    events = await ledger.get_session_events("sess-default")

    assert ledger_module.get_tenant_id() == "default"
    assert len(events) == 1
    assert events[0].tenant_id == "default"

    await conn.close()


@pytest.mark.asyncio
async def test_memory_event_ledger_keeps_hash_chain_isolated_per_tenant() -> None:
    from cortex.memory.ledger import EventLedgerL3

    conn = await aiosqlite.connect(":memory:")
    ledger = EventLedgerL3(conn)
    await ledger.ensure_table()

    alpha_first = _make_event(tenant_id="tenant-alpha", session_id="shared", content="alpha-1")
    beta_first = _make_event(tenant_id="tenant-beta", session_id="shared", content="beta-1")
    alpha_second = _make_event(tenant_id="tenant-alpha", session_id="shared", content="alpha-2")

    await ledger.append_event(alpha_first)
    await ledger.append_event(beta_first)
    await ledger.append_event(alpha_second)

    assert alpha_first.prev_hash == "GENESIS"
    assert beta_first.prev_hash == "GENESIS"
    assert alpha_second.prev_hash == alpha_first.signature

    assert (await ledger.verify_chain("tenant-alpha"))["status"] == "VALID"
    assert (await ledger.verify_chain("tenant-beta"))["status"] == "VALID"

    await conn.close()


@pytest.mark.asyncio
async def test_memory_event_ledger_detects_prev_hash_discontinuity() -> None:
    from cortex.memory.ledger import EventLedgerL3

    conn = await aiosqlite.connect(":memory:")
    ledger = EventLedgerL3(conn)
    await ledger.ensure_table()

    first = _make_event(tenant_id="tenant-alpha", session_id="sess-a", content="alpha-first")
    second = _make_event(tenant_id="tenant-alpha", session_id="sess-a", content="alpha-second")

    await ledger.append_event(first)
    await ledger.append_event(second)
    await conn.execute(
        "UPDATE memory_events SET prev_hash = 'BROKEN' WHERE event_id = ?",
        (second.event_id,),
    )
    await conn.commit()

    result = await ledger.verify_chain("tenant-alpha")

    assert result["status"] == "CORRUPT"
    assert any("DISCONTINUITY" in finding for finding in result["findings"])

    await conn.close()


def test_ledger_store_tx_rolls_back_and_wraps_errors(tmp_path: Path) -> None:
    from cortex.ledger.store import LedgerStore, LedgerStoreError

    store = LedgerStore(tmp_path / "ledger.db")

    with pytest.raises(LedgerStoreError, match="boom"):
        with store.tx() as conn:
            conn.execute(
                """
                INSERT INTO ledger_events (
                    event_id, ts, tool, actor, action, payload_json, prev_hash, hash, semantic_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-1",
                    "2026-04-14T00:00:00Z",
                    "test",
                    "codex",
                    "write",
                    "{}",
                    "GENESIS",
                    "hash-1",
                    "pending",
                ),
            )
            raise RuntimeError("boom")

    with store.tx() as conn:
        count = conn.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]
    assert count == 0


def test_ledger_store_backfills_legacy_attempt_columns(tmp_path: Path) -> None:
    from cortex.ledger.store import LedgerStore

    db_path = tmp_path / "legacy-ledger.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE enrichment_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE,
            event_id TEXT,
            fact_id INTEGER,
            job_type TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            attempts INTEGER NOT NULL DEFAULT 0,
            priority INTEGER DEFAULT 0,
            last_error TEXT,
            created_at TEXT NOT NULL DEFAULT '2026-04-14T00:00:00Z',
            updated_at TEXT NOT NULL DEFAULT '2026-04-14T00:00:00Z'
        );

        CREATE TABLE ledger_enrichment_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE,
            event_id TEXT,
            fact_id INTEGER,
            job_type TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            attempts INTEGER NOT NULL DEFAULT 0,
            priority INTEGER DEFAULT 0,
            last_error TEXT,
            created_at TEXT NOT NULL DEFAULT '2026-04-14T00:00:00Z',
            updated_at TEXT NOT NULL DEFAULT '2026-04-14T00:00:00Z'
        );
        """
    )
    conn.commit()
    conn.close()

    LedgerStore(db_path)

    conn = sqlite3.connect(db_path)
    enrichment_cols = {row[1] for row in conn.execute("PRAGMA table_info(enrichment_jobs)")}
    ledger_cols = {row[1] for row in conn.execute("PRAGMA table_info(ledger_enrichment_jobs)")}
    conn.close()

    assert {"next_attempt_ts", "next_attempt_at"} <= enrichment_cols
    assert {"next_attempt_ts", "next_attempt_at"} <= ledger_cols


def test_ledger_store_repairs_legacy_ledger_events_schema(tmp_path: Path) -> None:
    from cortex.ledger.store import LedgerStore

    db_path = tmp_path / "legacy-ledger-events.db"
    migration_sql = (
        Path("/Users/borjafernandezangulo/30_CORTEX/cortex/migrations/001_ledger_events.sql")
        .read_text()
    )

    conn = sqlite3.connect(db_path)
    conn.executescript(migration_sql)
    conn.commit()
    before = {row[1] for row in conn.execute("PRAGMA table_info(ledger_events)")}
    conn.close()

    LedgerStore(db_path)

    conn = sqlite3.connect(db_path)
    after = {row[1] for row in conn.execute("PRAGMA table_info(ledger_events)")}
    conn.close()

    assert before <= after
    assert {"prev_hash", "hash"} <= after


def test_ledger_store_backfills_legacy_next_attempt_columns(tmp_path: Path) -> None:
    from cortex.ledger.store import LedgerStore

    db_path = tmp_path / "legacy-enrichment-columns.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE ledger_events (
            event_id TEXT PRIMARY KEY,
            ts TEXT NOT NULL,
            tool TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            semantic_status TEXT NOT NULL DEFAULT 'pending'
        );

        CREATE TABLE enrichment_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE,
            event_id TEXT,
            fact_id INTEGER,
            job_type TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            attempts INTEGER NOT NULL DEFAULT 0,
            priority INTEGER DEFAULT 0,
            next_attempt_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL DEFAULT '2026-04-14T00:00:00Z',
            updated_at TEXT NOT NULL DEFAULT '2026-04-14T00:00:00Z'
        );

        CREATE TABLE ledger_enrichment_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE,
            event_id TEXT,
            fact_id INTEGER,
            job_type TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            attempts INTEGER NOT NULL DEFAULT 0,
            priority INTEGER DEFAULT 0,
            next_attempt_at TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL DEFAULT '2026-04-14T00:00:00Z',
            updated_at TEXT NOT NULL DEFAULT '2026-04-14T00:00:00Z'
        );

        INSERT INTO enrichment_jobs (
            job_id, event_id, status, attempts, priority, next_attempt_at, last_error, created_at, updated_at
        ) VALUES (
            'job-legacy', 'evt-legacy', 'retry', 1, 0, '2026-04-14T00:00:00+00:00', NULL,
            '2026-04-14T00:00:00Z', '2026-04-14T00:00:00Z'
        );

        INSERT INTO ledger_enrichment_jobs (
            job_id, event_id, status, attempts, priority, next_attempt_at, last_error, created_at, updated_at
        ) VALUES (
            'job-legacy', 'evt-legacy', 'retry', 1, 0, '2026-04-14T00:00:00+00:00', NULL,
            '2026-04-14T00:00:00Z', '2026-04-14T00:00:00Z'
        );
        """
    )
    conn.commit()
    conn.close()

    LedgerStore(db_path)

    conn = sqlite3.connect(db_path)
    job_row = conn.execute(
        "SELECT next_attempt_ts, next_attempt_at FROM enrichment_jobs WHERE job_id = 'job-legacy'"
    ).fetchone()
    ledger_job_row = conn.execute(
        "SELECT next_attempt_ts, next_attempt_at FROM ledger_enrichment_jobs WHERE job_id = 'job-legacy'"
    ).fetchone()
    conn.close()

    assert job_row[0] == job_row[1]
    assert ledger_job_row[0] == ledger_job_row[1]


def test_ledger_verifier_flags_failed_semantic_enrichment(tmp_path: Path) -> None:
    store, writer, verifier = _make_ledger_components(tmp_path / "verifier-failed.db")
    event_id = writer.append(_make_ledger_event(action="semantic-failure"))

    with store.tx() as conn:
        conn.execute(
            "UPDATE ledger_events SET semantic_status = 'failed' WHERE event_id = ?",
            (event_id,),
        )

    result = verifier.verify_chain()

    assert result["valid"] is False
    assert result["enrichment_stats"]["failed"] == 1
    assert any("Semantic enrichment failed" in violation for violation in result["violations"])


def test_ledger_verifier_reports_reconstruction_errors(tmp_path: Path) -> None:
    store, writer, verifier = _make_ledger_components(tmp_path / "verifier-bad-payload.db")
    event_id = writer.append(_make_ledger_event(action="bad-payload"))

    with store.tx() as conn:
        cursor = conn.execute(
            "SELECT payload_json FROM ledger_events WHERE event_id = ?",
            (event_id,),
        )
        payload = json.loads(cursor.fetchone()["payload_json"])
        payload.pop("target")
        conn.execute(
            "UPDATE ledger_events SET payload_json = ? WHERE event_id = ?",
            (json.dumps(payload), event_id),
        )

    result = verifier.verify_chain()

    assert result["valid"] is False
    assert any("Error parsing event" in violation for violation in result["violations"])


def test_ledger_verifier_skips_checkpoint_without_hashes() -> None:
    from contextlib import contextmanager

    from cortex.ledger.verifier import LedgerVerifier

    class DummyCursor:
        def __init__(self, *, one=None, many=None) -> None:
            self._one = one
            self._many = many or []

        def fetchone(self):
            return self._one

        def fetchall(self):
            return self._many

    rows = [
        {"event_id": "evt-1", "hash": None},
        {"event_id": "evt-2", "hash": None},
    ]

    def execute(sql: str, params: tuple[object, ...] = ()) -> DummyCursor:
        if "SELECT end_event_id FROM ledger_checkpoints" in sql:
            return DummyCursor(one=None)
        if "SELECT event_id, hash FROM ledger_events" in sql:
            assert params == (2,)
            return DummyCursor(many=rows)
        return DummyCursor()

    @contextmanager
    def tx():
        yield SimpleNamespace(execute=execute)

    verifier = LedgerVerifier(SimpleNamespace(tx=tx))

    assert verifier.create_checkpoint(batch_size=2) is None


def test_enrichment_queue_claims_oldest_eligible_job_and_marks_event_processing(
    tmp_path: Path,
) -> None:
    store, queue, writer, _ = _make_ledger_stack(tmp_path / "queue-claim.db")
    first_event_id = writer.append(_make_ledger_event(action="queued-first"))
    second_event_id = writer.append(_make_ledger_event(action="queued-second"))

    claimed = queue.claim_one()

    assert claimed is not None
    assert claimed["event_id"] == first_event_id
    assert claimed["attempts"] == 0

    with store.tx() as conn:
        first_job = conn.execute(
            "SELECT status FROM enrichment_jobs WHERE event_id = ?",
            (first_event_id,),
        ).fetchone()
        first_event = conn.execute(
            "SELECT semantic_status FROM ledger_events WHERE event_id = ?",
            (first_event_id,),
        ).fetchone()
        second_job = conn.execute(
            "SELECT status FROM enrichment_jobs WHERE event_id = ?",
            (second_event_id,),
        ).fetchone()

    assert first_job["status"] == "processing"
    assert first_event["semantic_status"] == "processing"
    assert second_job["status"] == "queued"


def test_enrichment_queue_returns_none_when_no_job_is_ready(tmp_path: Path) -> None:
    store, queue, writer, _ = _make_ledger_stack(tmp_path / "queue-empty.db")
    event_id = writer.append(_make_ledger_event(action="retry-later"))

    with store.tx() as conn:
        conn.execute(
            """
            UPDATE enrichment_jobs
            SET status = 'retry', next_attempt_ts = '2999-01-01T00:00:00+00:00'
            WHERE event_id = ?
            """,
            (event_id,),
        )

    assert queue.claim_one() is None


def test_enrichment_queue_enqueue_wrapper_persists_dual_next_attempt_columns(
    tmp_path: Path,
) -> None:
    store, queue, writer, _ = _make_ledger_stack(tmp_path / "queue-enqueue.db")
    event_id = writer.append(_make_ledger_event(action="manual-enqueue"))

    job_id = queue.enqueue(event_id)

    with store.tx() as conn:
        job_row = conn.execute(
            """
            SELECT status, next_attempt_ts, next_attempt_at
            FROM enrichment_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()

    assert job_row["status"] == "queued"
    assert job_row["next_attempt_ts"] is not None
    assert job_row["next_attempt_at"] is not None


def test_enrichment_queue_mark_done_indexes_event_and_clears_error(tmp_path: Path) -> None:
    store, queue, writer, _ = _make_ledger_stack(tmp_path / "queue-done.db")
    event_id = writer.append(_make_ledger_event(action="done"))

    with store.tx() as conn:
        job_id = conn.execute(
            "SELECT job_id FROM enrichment_jobs WHERE event_id = ?",
            (event_id,),
        ).fetchone()["job_id"]
        conn.execute(
            "UPDATE ledger_events SET semantic_error = 'stale error' WHERE event_id = ?",
            (event_id,),
        )

    queue.mark_done(job_id, event_id)

    with store.tx() as conn:
        job_row = conn.execute(
            "SELECT status FROM enrichment_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        event_row = conn.execute(
            "SELECT semantic_status, semantic_error FROM ledger_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()

    assert job_row["status"] == "done"
    assert event_row["semantic_status"] == "indexed"
    assert event_row["semantic_error"] is None


def test_enrichment_queue_mark_failed_retries_with_truncated_error(tmp_path: Path) -> None:
    from datetime import datetime

    from cortex.ledger.models import utc_now_iso

    store, queue, writer, _ = _make_ledger_stack(tmp_path / "queue-retry.db")
    event_id = writer.append(_make_ledger_event(action="retry"))
    error = "x" * 2100

    with store.tx() as conn:
        job_id = conn.execute(
            "SELECT job_id FROM enrichment_jobs WHERE event_id = ?",
            (event_id,),
        ).fetchone()["job_id"]

    queue.mark_failed(job_id, event_id, error, attempts=1)

    with store.tx() as conn:
        job_row = conn.execute(
            """
            SELECT status, attempts, next_attempt_ts, next_attempt_at, last_error
            FROM enrichment_jobs
            WHERE job_id = ?
            """,
            (job_id,),
        ).fetchone()
        event_row = conn.execute(
            "SELECT semantic_status, semantic_error FROM ledger_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()

    assert job_row["status"] == "retry"
    assert job_row["attempts"] == 2
    assert len(job_row["last_error"]) == 2000
    assert job_row["next_attempt_ts"] == job_row["next_attempt_at"]
    assert datetime.fromisoformat(job_row["next_attempt_ts"]) > datetime.fromisoformat(
        utc_now_iso()
    )
    assert event_row["semantic_status"] == "pending"
    assert event_row["semantic_error"] == error[:2000]


def test_enrichment_queue_mark_failed_becomes_terminal_after_max_attempts(
    tmp_path: Path,
) -> None:
    store, queue, writer, _ = _make_ledger_stack(tmp_path / "queue-terminal.db")
    event_id = writer.append(_make_ledger_event(action="terminal"))

    with store.tx() as conn:
        job_id = conn.execute(
            "SELECT job_id FROM enrichment_jobs WHERE event_id = ?",
            (event_id,),
        ).fetchone()["job_id"]

    queue.mark_failed(job_id, event_id, "permanent failure", attempts=8)

    with store.tx() as conn:
        job_row = conn.execute(
            "SELECT status, attempts, last_error FROM enrichment_jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        event_row = conn.execute(
            "SELECT semantic_status, semantic_error FROM ledger_events WHERE event_id = ?",
            (event_id,),
        ).fetchone()

    assert job_row["status"] == "failed"
    assert job_row["attempts"] == 9
    assert job_row["last_error"] == "permanent failure"
    assert event_row["semantic_status"] == "failed"
    assert event_row["semantic_error"] == "permanent failure"


def test_working_memory_falls_back_to_default_tenant_when_security_extension_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    original_import = builtins.__import__

    def broken_import(name: str, *args: object, **kwargs: object):
        if name == "cortex.extensions.security.tenant":
            raise ImportError("tenant extension unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", broken_import)
    sys.modules.pop("cortex.memory.working", None)
    working_module = importlib.import_module("cortex.memory.working")
    WorkingMemoryL1 = working_module.WorkingMemoryL1

    l1 = WorkingMemoryL1(max_tokens=10)
    l1.add_event(_make_event(tenant_id="default", session_id="wm-default", content="hello"))

    assert working_module.get_tenant_id() == "default"
    assert l1.get_context() == [{"role": "user", "content": "hello"}]
    assert l1.current_tokens == 1


def test_working_memory_access_frequency_is_zero_with_empty_log() -> None:
    from cortex.memory.working import WorkingMemoryL1

    l1 = WorkingMemoryL1(max_tokens=10)

    assert l1.get_access_frequency("tenant-empty:proj") == 0.0


def test_working_memory_snapshot_returns_empty_payload_for_unknown_tenant() -> None:
    from cortex.memory.working import WorkingMemoryL1

    l1 = WorkingMemoryL1(max_tokens=10)

    assert l1.snapshot("missing-tenant") == {
        "tenant_id": "missing-tenant",
        "tokens": 0,
        "events": [],
    }


def test_working_memory_restore_rejects_empty_resolved_tenant() -> None:
    import cortex.memory.working as working_module

    WorkingMemoryL1 = working_module.WorkingMemoryL1

    l1 = WorkingMemoryL1(max_tokens=10)
    original_get_tenant_id = working_module.get_tenant_id
    working_module.get_tenant_id = lambda: ""

    try:
        with pytest.raises(ValueError, match="resolved tenant_id is None or empty"):
            l1.restore({"tenant_id": "", "events": []}, tenant_id="")
    finally:
        working_module.get_tenant_id = original_get_tenant_id


def test_working_memory_restore_accepts_prebuilt_event_instances() -> None:
    from cortex.memory.working import WorkingMemoryL1

    event = _make_event(tenant_id="tenant-prebuilt", session_id="wm-restore", content="rehydrated")
    l1 = WorkingMemoryL1(max_tokens=10)

    l1.restore({"events": [event], "tokens": event.token_count}, tenant_id="tenant-prebuilt")

    assert l1.get_context("tenant-prebuilt") == [{"role": "user", "content": "rehydrated"}]
    assert l1.snapshot("tenant-prebuilt")["tokens"] == event.token_count


def test_working_memory_utilization_defensively_handles_zero_budget() -> None:
    from cortex.memory.working import WorkingMemoryL1

    l1 = WorkingMemoryL1(max_tokens=1)
    l1._max_tokens = 0

    assert l1.utilization("any-tenant") == 0.0


@pytest.mark.asyncio
async def test_trust_batch_update_skips_missing_facts_and_preserves_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    update_mock = AsyncMock(
        side_effect=[_make_trust_update(1), ValueError("missing fact"), _make_trust_update(3)]
    )
    monkeypatch.setattr(BayesianTrustUpdater, "update", update_mock)

    updater = BayesianTrustUpdater(MagicMock())
    results = await updater.batch_update([1, 2, 3], Signal.CONFIRM, tenant_id="tenant-scope")

    assert [result.fact_id for result in results] == [1, 3]
    assert [call.args for call in update_mock.await_args_list] == [
        (1, Signal.CONFIRM, "tenant-scope"),
        (2, Signal.CONFIRM, "tenant-scope"),
        (3, Signal.CONFIRM, "tenant-scope"),
    ]


@pytest.mark.asyncio
async def test_trust_inspect_reports_upgrade_requirements_for_explicit_tenant() -> None:
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=("C2", None))
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=cursor)
    engine = MagicMock()
    engine.get_conn = AsyncMock(return_value=conn)

    result = await BayesianTrustUpdater(engine).inspect(42, tenant_id="tenant-42")

    assert conn.execute.await_args.args[1] == (42, "tenant-42")
    assert result["confidence"] == "C2"
    assert result["prior_alpha"] == 3.0
    assert result["prior_beta"] == 7.0
    assert set(result["required_to_upgrade"]) == {"C3", "C4", "C5"}


@pytest.mark.asyncio
async def test_trust_inspect_raises_when_fact_is_missing() -> None:
    cursor = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=None)
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=cursor)
    engine = MagicMock()
    engine.get_conn = AsyncMock(return_value=conn)

    with pytest.raises(ValueError, match="not found"):
        await BayesianTrustUpdater(engine).inspect(404, tenant_id="tenant-missing")


@pytest.mark.asyncio
async def test_apply_semantic_dedup_fails_open_when_recall_raises() -> None:
    class DummySemanticMixin:
        _thermal_decay_cache: dict[int, int] = {}

        def __init__(self) -> None:
            self._memory_manager = SimpleNamespace(
                _l2=SimpleNamespace(recall=AsyncMock(side_effect=RuntimeError("l2-down"))),
            )

    result = await sv._apply_semantic_dedup(
        DummySemanticMixin(),
        conn=AsyncMock(),
        project="proj-c",
        content="dedup fallback",
        tenant_id="tenant-c",
    )

    assert result is None


@pytest.mark.asyncio
async def test_apply_semantic_dedup_returns_none_for_empty_recall() -> None:
    class DummySemanticMixin:
        _thermal_decay_cache: dict[int, int] = {}

        def __init__(self) -> None:
            self._memory_manager = SimpleNamespace(
                _l2=SimpleNamespace(recall=AsyncMock(return_value=[])),
            )

    result = await sv._apply_semantic_dedup(
        DummySemanticMixin(),
        conn=AsyncMock(),
        project="proj-empty",
        content="dedup empty",
        tenant_id="tenant-empty",
    )

    assert result is None


@pytest.mark.asyncio
async def test_check_byzantine_auth_blocks_os_command_without_consensus() -> None:
    auth = MagicMock()
    auth.acquire_lock = AsyncMock(return_value=False)
    mixin = SimpleNamespace(auth=auth)

    with pytest.raises(PermissionError, match="Byzantine consensus failed"):
        await sv._check_byzantine_auth(
            mixin,
            meta={"intent": "OS_COMMAND"},
            source="agent:ops",
            tenant_id="tenant-ops",
        )

    auth.acquire_lock.assert_awaited_once_with("OS_COMMAND", "agent:ops")


def test_enforce_thermodynamics_blocks_non_error_write_in_decorative_mode() -> None:
    from cortex.guards.thermodynamic import AgentMode

    cls = SimpleNamespace(_agent_mode=AgentMode.DECORATIVE)

    with pytest.raises(RuntimeError, match="DECORATIVE mode"):
        sv._enforce_thermodynamics(cls, fact_type="knowledge", skip_thermo=False)


@pytest.mark.asyncio
async def test_apply_semantic_dedup_updates_last_accessed_for_near_duplicate() -> None:
    class DummySemanticMixin:
        _thermal_decay_cache: dict[int, int] = {}

        def __init__(self, recall: AsyncMock) -> None:
            self._memory_manager = SimpleNamespace(_l2=SimpleNamespace(recall=recall))

    conn = AsyncMock()
    top = SimpleNamespace(id="7", _recall_score=0.97)
    mixin = DummySemanticMixin(AsyncMock(return_value=[top]))
    DummySemanticMixin._thermal_decay_cache = {}

    result = await sv._apply_semantic_dedup(
        mixin,
        conn=conn,
        project="proj-a",
        content="semantically close fact",
        tenant_id="tenant-a",
    )

    assert result == 7
    conn.execute.assert_awaited_once_with(
        "UPDATE facts SET last_accessed = CURRENT_TIMESTAMP WHERE id=?",
        (7,),
    )
    assert DummySemanticMixin._thermal_decay_cache[7] == 1


@pytest.mark.asyncio
async def test_apply_semantic_dedup_deprecates_after_repeated_thermal_decay() -> None:
    class DummySemanticMixin:
        _thermal_decay_cache: dict[int, int] = {}

        def __init__(self, recall: AsyncMock, deprecate: AsyncMock) -> None:
            self._memory_manager = SimpleNamespace(_l2=SimpleNamespace(recall=recall))
            self.deprecate = deprecate

    conn = AsyncMock()
    top = SimpleNamespace(id="11", _recall_score=0.99)
    mixin = DummySemanticMixin(AsyncMock(return_value=[top]), AsyncMock(return_value=True))
    DummySemanticMixin._thermal_decay_cache = {11: 4}

    result = await sv._apply_semantic_dedup(
        mixin,
        conn=conn,
        project="proj-b",
        content="thermal decay candidate",
        tenant_id="tenant-b",
    )

    assert result == 11
    mixin.deprecate.assert_awaited_once_with(11, "Thermal decay (5x)", conn, "tenant-b")
    assert DummySemanticMixin._thermal_decay_cache[11] == 0


@pytest.mark.asyncio
async def test_run_store_validation_applies_exergy_bridge_and_membrane_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cortex.engine.bridge_guard as bridge_guard
    import cortex.engine.fact_store_core as fact_store_core
    import cortex.engine.guard_integration_patch as guard_integration_patch
    import cortex.engine.membrane.sanitizer as sanitizer
    import cortex.engine.nemesis as nemesis
    import cortex.engine.storage_guard as storage_guard
    import cortex.engine.store_validators as store_validators
    import cortex.guards.thermodynamic as thermodynamic
    import cortex.shannon.exergy as exergy
    from cortex.guards.thermodynamic import AgentMode

    class DummyPure:
        def __init__(self, content: str, metadata: dict[str, object]) -> None:
            self.content = content
            self.metadata = metadata

    class LegacyMembraneLog:
        def dict(self) -> dict[str, str]:
            return {"mode": "legacy"}

    class DummyMixin:
        _agent_mode = AgentMode.ACTIVE
        _thermo_counters: object = object()

        def _apply_privacy_shield(
            self, content: str, project: str, meta: dict[str, object]
        ) -> dict[str, object]:
            return {**meta, "privacy_shield": True}

    conn = AsyncMock()
    enforce_store_guards = AsyncMock(return_value=None)

    monkeypatch.delenv("CORTEX_SKIP_EXERGY_VALIDATION", raising=False)
    monkeypatch.setattr(storage_guard.StorageGuard, "validate", lambda **_: None)
    monkeypatch.setattr(store_validators, "validate_content", lambda project, content, _: content)
    monkeypatch.setattr(store_validators, "check_dedup", AsyncMock(return_value=None))
    monkeypatch.setattr(
        sanitizer.SovereignSanitizer,
        "digest",
        staticmethod(
            lambda raw_engram: (
                DummyPure(raw_engram["content"], raw_engram["metadata"]),
                LegacyMembraneLog(),
            )
        ),
    )
    monkeypatch.setattr(
        fact_store_core,
        "resolve_causality_async",
        AsyncMock(side_effect=lambda _conn, _project, meta: meta),
    )
    monkeypatch.setattr(nemesis.NemesisProtocol, "analyze_async", AsyncMock(return_value=None))
    monkeypatch.setattr(
        bridge_guard.BridgeGuard,
        "detect_bridge_candidate",
        AsyncMock(return_value="source-proj"),
    )
    monkeypatch.setattr(
        bridge_guard.BridgeGuard,
        "validate_bridge",
        AsyncMock(return_value={"meta_flags": {"bridge_flag": True}}),
    )
    monkeypatch.setattr(guard_integration_patch, "enforce_store_guards", enforce_store_guards)
    monkeypatch.setattr(
        exergy,
        "calculate_exergy",
        lambda *_args, **_kwargs: SimpleNamespace(exergy_score=0.42),
    )
    monkeypatch.setattr(exergy, "enforce_exergy", lambda _result: None)
    monkeypatch.setattr(
        thermodynamic,
        "should_enter_decorative_mode",
        lambda _counters: (True, ["thermo-threshold"]),
    )

    dedupe_id, meta, content, fact_type = await sv.run_store_validation_logic(
        mixin_instance=DummyMixin(),
        conn=conn,
        project="dest-proj",
        content="bridgeable fact",
        tenant_id="tenant-x",
        fact_type="knowledge",
        tags=["critical"],
        confidence="C3",
        source="agent:test",
        meta={"_prior_entropy": 1.0, "_posterior_entropy": 0.25},
    )

    assert dedupe_id is None
    assert fact_type == "bridge"
    assert content.startswith("Pattern from source-proj")
    assert meta is not None
    assert meta["_exergy_score"] == 0.42
    assert meta["_membrane_log"] == {"mode": "legacy"}
    assert meta["bridge_flag"] is True
    assert meta["privacy_shield"] is True
    assert DummyMixin._agent_mode == AgentMode.DECORATIVE
    enforce_store_guards.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_store_validation_returns_exact_dedup_hit_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cortex.engine.fact_store_core as fact_store_core
    import cortex.engine.guard_integration_patch as guard_integration_patch
    import cortex.engine.nemesis as nemesis
    import cortex.engine.storage_guard as storage_guard
    import cortex.engine.store_validators as store_validators

    class DummyMixin:
        _agent_mode = object()

        def _apply_privacy_shield(self, content: str, project: str, meta: dict[str, object] | None):
            return meta

    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")
    monkeypatch.setattr(storage_guard.StorageGuard, "validate", lambda **_: None)
    monkeypatch.setattr(store_validators, "validate_content", lambda project, content, _: content)
    monkeypatch.setattr(store_validators, "check_dedup", AsyncMock(return_value=123))
    monkeypatch.setattr(guard_integration_patch, "enforce_store_guards", AsyncMock())
    monkeypatch.setattr(
        fact_store_core,
        "resolve_causality_async",
        AsyncMock(side_effect=lambda _conn, _project, meta: meta),
    )
    monkeypatch.setattr(nemesis.NemesisProtocol, "analyze_async", AsyncMock(return_value=None))

    result = await sv.run_store_validation_logic(
        mixin_instance=DummyMixin(),
        conn=AsyncMock(),
        project="proj-dedup",
        content="exact dedup",
        tenant_id="tenant-dedup",
        fact_type="knowledge",
        tags=None,
        confidence="C3",
        source="agent:test",
        meta=None,
    )

    assert result == (123, None, "exact dedup", "knowledge")


@pytest.mark.asyncio
async def test_run_store_validation_returns_semantic_dedup_hit_without_full_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cortex.engine.fact_store_core as fact_store_core
    import cortex.engine.guard_integration_patch as guard_integration_patch
    import cortex.engine.nemesis as nemesis
    import cortex.engine.storage_guard as storage_guard
    import cortex.engine.store_validators as store_validators

    class DummyMixin:
        _agent_mode = object()

        def _apply_privacy_shield(self, content: str, project: str, meta: dict[str, object] | None):
            return meta

    semantic_dedup = AsyncMock(return_value=456)

    monkeypatch.setenv("CORTEX_SKIP_EXERGY_VALIDATION", "1")
    monkeypatch.setattr(storage_guard.StorageGuard, "validate", lambda **_: None)
    monkeypatch.setattr(store_validators, "validate_content", lambda project, content, _: content)
    monkeypatch.setattr(store_validators, "check_dedup", AsyncMock(return_value=None))
    monkeypatch.setattr(sv, "_apply_semantic_dedup", semantic_dedup)
    monkeypatch.setattr(guard_integration_patch, "enforce_store_guards", AsyncMock())
    monkeypatch.setattr(
        fact_store_core,
        "resolve_causality_async",
        AsyncMock(side_effect=lambda _conn, _project, meta: meta),
    )
    monkeypatch.setattr(nemesis.NemesisProtocol, "analyze_async", AsyncMock(return_value=None))

    result = await sv.run_store_validation_logic(
        mixin_instance=DummyMixin(),
        conn=AsyncMock(),
        project="proj-semantic",
        content="semantic dedup",
        tenant_id="tenant-semantic",
        fact_type="knowledge",
        tags=None,
        confidence="C3",
        source="agent:test",
        meta=None,
    )

    assert result == (456, None, "semantic dedup", "knowledge")


@pytest.mark.asyncio
async def test_run_store_validation_resets_active_mode_without_entropy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cortex.engine.bridge_guard as bridge_guard
    import cortex.engine.fact_store_core as fact_store_core
    import cortex.engine.guard_integration_patch as guard_integration_patch
    import cortex.engine.membrane.sanitizer as sanitizer
    import cortex.engine.nemesis as nemesis
    import cortex.engine.storage_guard as storage_guard
    import cortex.engine.store_validators as store_validators
    from cortex.guards.thermodynamic import AgentMode

    class DummyPure:
        def __init__(self, content: str, metadata: dict[str, object]) -> None:
            self.content = content
            self.metadata = metadata

    class DummyMembraneLog:
        def model_dump(self) -> dict[str, str]:
            return {"mode": "pydantic"}

    class DummyMixin:
        _agent_mode = AgentMode.ACTIVE
        _thermo_counters: object = object()

        def _apply_privacy_shield(
            self, content: str, project: str, meta: dict[str, object] | None
        ) -> dict[str, object]:
            return dict(meta or {})

    monkeypatch.delenv("CORTEX_SKIP_EXERGY_VALIDATION", raising=False)
    monkeypatch.setattr(storage_guard.StorageGuard, "validate", lambda **_: None)
    monkeypatch.setattr(store_validators, "validate_content", lambda project, content, _: content)
    monkeypatch.setattr(store_validators, "check_dedup", AsyncMock(return_value=None))
    monkeypatch.setattr(
        sanitizer.SovereignSanitizer,
        "digest",
        staticmethod(
            lambda raw_engram: (
                DummyPure(raw_engram["content"], raw_engram["metadata"]),
                DummyMembraneLog(),
            )
        ),
    )
    monkeypatch.setattr(
        fact_store_core,
        "resolve_causality_async",
        AsyncMock(side_effect=lambda _conn, _project, meta: meta),
    )
    monkeypatch.setattr(nemesis.NemesisProtocol, "analyze_async", AsyncMock(return_value=None))
    monkeypatch.setattr(
        bridge_guard.BridgeGuard,
        "detect_bridge_candidate",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(guard_integration_patch, "enforce_store_guards", AsyncMock())

    dedupe_id, meta, content, fact_type = await sv.run_store_validation_logic(
        mixin_instance=DummyMixin(),
        conn=AsyncMock(),
        project="proj-active",
        content="plain fact",
        tenant_id="tenant-active",
        fact_type="knowledge",
        tags=None,
        confidence="C3",
        source="agent:test",
        meta=None,
    )

    assert dedupe_id is None
    assert content == "plain fact"
    assert fact_type == "knowledge"
    assert meta is not None
    assert meta["_membrane_log"] == {"mode": "pydantic"}
    assert DummyMixin._agent_mode == AgentMode.ACTIVE


@pytest.mark.asyncio
async def test_run_store_validation_fails_closed_when_dependencies_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    original_import = builtins.__import__

    def broken_import(name: str, *args: object, **kwargs: object):
        if name == "cortex.engine.bridge_guard":
            raise ImportError("bridge guard unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", broken_import)

    with pytest.raises(RuntimeError, match="FAIL-CLOSED"):
        await sv.run_store_validation_logic(
            mixin_instance=SimpleNamespace(),
            conn=AsyncMock(),
            project="proj-dead",
            content="should fail closed",
            tenant_id="tenant-dead",
            fact_type="knowledge",
            tags=None,
            confidence="C3",
            source="agent:test",
            meta=None,
        )


def test_session_guardrail_utilization_is_zero_with_non_positive_budget() -> None:
    from cortex.memory.guardrails import SessionGuardrail

    guardrail = SessionGuardrail(max_tokens=0)

    assert guardrail.utilization == 0.0
    assert guardrail.status()["utilization"] == 0.0


def test_session_guardrail_exposes_turn_counter_property() -> None:
    from cortex.memory.guardrails import SessionGuardrail

    guardrail = SessionGuardrail(max_tokens=100)
    guardrail.tick_turn()
    guardrail.tick_turn()

    assert guardrail.turns == 2
