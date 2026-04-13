from __future__ import annotations

import sqlite3
import time

import pytest

from cortex.telemetry.quality import MemoryQualityEvaluator, QualityScanError


class _SovereignStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def _get_conn(self) -> sqlite3.Connection:
        return self._conn


@pytest.mark.asyncio
async def test_calculate_stale_memory_ratio_records_gauge(monkeypatch: pytest.MonkeyPatch):
    import cortex.telemetry.quality as quality

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            """
            CREATE TABLE facts (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                project TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        now = time.time()
        conn.executemany(
            "INSERT INTO facts (tenant_id, project, created_at) VALUES (?, ?, ?)",
            [
                ("tenant-alpha", "alpha", now - (100 * 86400)),
                ("tenant-alpha", "alpha", now - (10 * 86400)),
            ],
        )
        conn.commit()

        recorded: list[tuple[str, float, dict[str, str]]] = []

        def fake_set_gauge(name: str, value: float, labels: dict[str, str]) -> None:
            recorded.append((name, value, labels))

        monkeypatch.setattr(quality.metrics, "set_gauge", fake_set_gauge)

        evaluator = MemoryQualityEvaluator(_SovereignStore(conn))
        await evaluator._calculate_stale_memory_ratio("tenant-alpha", "alpha", stale_days=90)

        assert recorded == [
            (
                "cortex_stale_memory_ratio",
                0.5,
                {"tenant_id": "tenant-alpha", "project_id": "alpha"},
            )
        ]
    finally:
        conn.close()


@pytest.mark.asyncio
async def test_calculate_stale_memory_ratio_requires_sovereign_store():
    evaluator = MemoryQualityEvaluator(object())

    with pytest.raises(QualityScanError, match="requires sovereign store"):
        await evaluator._calculate_stale_memory_ratio("tenant-alpha", "alpha")


@pytest.mark.asyncio
async def test_run_quality_scan_fails_closed_on_db_error():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        evaluator = MemoryQualityEvaluator(_SovereignStore(conn))

        with pytest.raises(QualityScanError, match="Failed to calculate stale memory ratio"):
            await evaluator.run_quality_scan("tenant-alpha", "alpha")
    finally:
        conn.close()
