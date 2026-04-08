from __future__ import annotations

import asyncio

import pytest

from cortex.engine.mixins.optimization import OptimizationMixin


class _OptimizationHarness(OptimizationMixin):
    def __init__(self) -> None:
        super().__init__()
        self.seen_batches: list[list[object]] = []

    async def _flush_batch(self, batch: list) -> None:
        self.seen_batches.append(list(batch))


@pytest.mark.asyncio
async def test_process_batch_passes_copy_to_flush_task() -> None:
    harness = _OptimizationHarness()
    batch = [("future", "INSERT INTO facts VALUES (?)", (1,))]

    harness._process_batch(batch)
    await asyncio.sleep(0)

    assert batch == []
    assert harness.seen_batches == [[("future", "INSERT INTO facts VALUES (?)", (1,))]]
