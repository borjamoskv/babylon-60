from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest

from cortex.engine.transaction_mixin import TransactionMixin
from cortex.utils.canonical import compute_tx_hash


class _DummyTransactionEngine(TransactionMixin):
    def __init__(self, *, ledger: Any = None, pool: Any = None) -> None:
        self._ledger = ledger
        self.pool = pool


class _FakeCursor:
    def __init__(self, row: Any) -> None:
        self._row = row

    async def fetchone(self) -> Any:
        return self._row

    async def close(self) -> None:
        return None


class _AwaitableCursor:
    def __init__(self, row: Any) -> None:
        self._cursor = _FakeCursor(row)

    def __await__(self):
        async def _resolve():
            return self._cursor

        return _resolve().__await__()

    async def __aenter__(self) -> _FakeCursor:
        return self._cursor

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.fixture
async def tx_conn():
    conn = await aiosqlite.connect(":memory:")
    await conn.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            project TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            prev_hash TEXT NOT NULL,
            hash TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    await conn.commit()
    try:
        yield conn
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_log_transaction_skips_checkpoint_when_disabled(tx_conn) -> None:
    ledger = MagicMock()
    ledger.create_checkpoint_async = AsyncMock()
    engine = _DummyTransactionEngine(ledger=ledger)

    tx_id = await engine._log_transaction(
        tx_conn,
        "trust-core",
        "store",
        {"fact_type": "knowledge"},
        tenant_id="tenant-a",
        checkpoint=False,
    )

    assert tx_id == 1
    ledger.record_write.assert_not_called()
    ledger.create_checkpoint_async.assert_not_awaited()

    cursor = await tx_conn.execute("SELECT COUNT(*) FROM transactions WHERE tenant_id = ?", ("tenant-a",))
    row = await cursor.fetchone()
    await cursor.close()
    assert row[0] == 1


@pytest.mark.asyncio
async def test_log_transaction_recomputes_hash_when_db_prev_hash_differs(
    tx_conn: aiosqlite.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    await tx_conn.execute(
        """
        INSERT INTO transactions (tenant_id, project, action, detail, prev_hash, hash, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "tenant-a",
            "trust-core",
            "seed",
            "{}",
            "GENESIS",
            "prev-real-hash",
            "2026-04-14T00:00:00Z",
        ),
    )
    await tx_conn.commit()

    import cortex.engine.transaction_mixin as transaction_module

    monkeypatch.setattr(transaction_module, "now_iso", lambda: "2026-04-14T12:00:00Z")

    original_execute = tx_conn.execute

    def patched_execute(sql: str, params=()):
        if sql.startswith("SELECT hash FROM transactions WHERE tenant_id = ?"):
            return _AwaitableCursor(None)
        return original_execute(sql, params)

    monkeypatch.setattr(tx_conn, "execute", patched_execute)

    engine = _DummyTransactionEngine()
    tx_id = await engine._log_transaction(
        tx_conn,
        "trust-core",
        "store",
        {"fact_type": "knowledge"},
        tenant_id="tenant-a",
        checkpoint=False,
    )

    cursor = await original_execute("SELECT prev_hash, hash FROM transactions WHERE id = ?", (tx_id,))
    row = await cursor.fetchone()
    await cursor.close()

    assert row[0] == "prev-real-hash"
    assert row[1] == compute_tx_hash(
        "prev-real-hash",
        "trust-core",
        "store",
        '{"fact_type":"knowledge"}',
        "2026-04-14T12:00:00Z",
    )


@pytest.mark.asyncio
async def test_log_transaction_records_metric_when_checkpoint_fails(
    tx_conn: aiosqlite.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = MagicMock()
    ledger.create_checkpoint_async = AsyncMock(side_effect=RuntimeError("checkpoint failed"))
    engine = _DummyTransactionEngine(ledger=ledger)

    from cortex.telemetry.metrics import metrics

    inc = MagicMock()
    monkeypatch.setattr(metrics, "inc", inc)

    tx_id = await engine._log_transaction(
        tx_conn,
        "trust-core",
        "store",
        {"fact_type": "knowledge"},
        tenant_id="tenant-a",
        checkpoint=True,
    )

    assert tx_id == 1
    ledger.record_write.assert_called_once()
    ledger.create_checkpoint_async.assert_awaited_once()
    inc.assert_called_once()
    assert inc.call_args.args[0] == "cortex_ledger_checkpoint_failures_total"


@pytest.mark.asyncio
async def test_verify_ledger_uses_existing_ledger() -> None:
    ledger = MagicMock()
    ledger.audit_integrity_async = AsyncMock(return_value={"valid": True})
    engine = _DummyTransactionEngine(ledger=ledger)

    result = await engine.verify_ledger()

    assert result == {"valid": True}
    ledger.audit_integrity_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_ledger_initializes_immutable_ledger_from_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_with: list[Any] = []

    class FakeImmutableLedger:
        def __init__(self, pool: Any) -> None:
            created_with.append(pool)

        async def audit_integrity_async(self) -> dict[str, Any]:
            return {"valid": True, "source": "lazy"}

    import cortex.ledger as ledger_module

    monkeypatch.setattr(ledger_module, "ImmutableLedger", FakeImmutableLedger)

    pool = object()
    engine = _DummyTransactionEngine(pool=pool)

    result = await engine.verify_ledger()

    assert result == {"valid": True, "source": "lazy"}
    assert created_with == [pool]
    assert isinstance(engine._ledger, FakeImmutableLedger)
