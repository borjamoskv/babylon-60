from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiosqlite
import pytest

from cortex.database.schema import CREATE_FACTS
from cortex.engine.guard_adapters import EpistemicBreakerHook
from cortex.extensions.daemon.epistemic_breaker import EpistemicBreakerDaemon


async def _build_facts_table(conn: aiosqlite.Connection) -> None:
    await conn.execute(CREATE_FACTS)
    await conn.commit()


@pytest.mark.asyncio
async def test_evaluate_uses_current_facts_schema_with_parent_id() -> None:
    conn = await aiosqlite.connect(":memory:")
    try:
        await _build_facts_table(conn)
        await conn.executemany(
            """
            INSERT INTO facts (tenant_id, project, content, fact_type, is_tombstoned, parent_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("tenant-a", "alpha", "decision-1", "decision", 0, None),
                ("tenant-a", "alpha", "error-1", "error", 0, 1),
                ("tenant-a", "alpha", "old", "decision", 1, None),
            ],
        )
        await conn.commit()

        result = await EpistemicBreakerDaemon.evaluate(conn, "tenant-a", "alpha")
    finally:
        await conn.close()

    assert result["tripped"] is False
    assert result["stats"]["total_facts"] == 3
    assert result["stats"]["active_facts"] == 2
    assert result["stats"]["deprecated_facts"] == 1
    assert result["stats"]["orphan_facts"] == 1
    assert result["stats"]["types"]["error"] == 1
    assert result["entropy"] == pytest.approx(0.3417, abs=1e-4)


@pytest.mark.asyncio
async def test_evaluate_returns_clean_result_when_facts_table_is_missing() -> None:
    conn = await aiosqlite.connect(":memory:")
    try:
        result = await EpistemicBreakerDaemon.evaluate(conn, "tenant-a", "alpha")
    finally:
        await conn.close()

    assert result["tripped"] is False
    assert result["entropy"] == 0.0
    assert result["stats"]["total_facts"] == 0


@pytest.mark.asyncio
async def test_evaluate_logs_when_entropy_threshold_is_crossed(caplog: pytest.LogCaptureFixture) -> None:
    conn = await aiosqlite.connect(":memory:")
    try:
        await _build_facts_table(conn)
        await conn.executemany(
            """
            INSERT INTO facts (tenant_id, project, content, fact_type, is_tombstoned)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("tenant-a", "alpha", "error-1", "error", 0),
                ("tenant-a", "alpha", "error-2", "error", 0),
                ("tenant-a", "alpha", "old", "knowledge", 1),
            ],
        )
        await conn.commit()

        with caplog.at_level("WARNING"):
            result = await EpistemicBreakerDaemon.evaluate(
                conn,
                "tenant-a",
                "alpha",
                max_entropy_threshold=0.5,
            )
    finally:
        await conn.close()

    assert result["tripped"] is True
    assert "[EPISTEMIC BREAKER] Post-store entropy threshold crossed" in caplog.text


@pytest.mark.asyncio
async def test_epistemic_breaker_hook_calls_one_shot_evaluate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evaluate = AsyncMock(return_value={"entropy": 0.0, "tripped": False, "stats": {}})
    monkeypatch.setattr(
        "cortex.extensions.daemon.epistemic_breaker.EpistemicBreakerDaemon.evaluate",
        evaluate,
    )

    hook = EpistemicBreakerHook()
    conn = MagicMock()

    await hook.on_stored(
        fact_id=7,
        project="alpha",
        fact_type="decision",
        conn=conn,
        tenant_id="tenant-a",
    )

    evaluate.assert_awaited_once_with(conn, "tenant-a", "alpha")
