"""Tests for CORTEX-SWARM-10K Sharded Architecture."""

from pathlib import Path

import pytest

from cortex import config
from cortex.engine.swarm_10k import SwarmCommander
from cortex.extensions.signals.sharded_bus import ShardedAsyncSignalBus, ShardedDurableSignalBus


@pytest.mark.asyncio
async def test_sharded_signal_bus_initialization(tmp_path: Path):
    """Test that the sharded bus initializes all 16 shards correctly."""
    bus = ShardedDurableSignalBus(base_dir=tmp_path)
    await bus.initialize()

    assert len(bus._shards) == bus.num_shards
    for i in range(bus.num_shards):
        db_file = tmp_path / f"swarm_shard_{i:03d}.db"
        assert db_file.exists(), f"Shard {i} must exist"

    await bus.close()


def test_sharded_signal_bus_legacy_name_is_alias() -> None:
    assert ShardedAsyncSignalBus is ShardedDurableSignalBus


@pytest.mark.asyncio
async def test_swarm_commander_hierarchy(tmp_path: Path):
    """Test L0 to L2 hierarchy generation."""
    commander = SwarmCommander(bus_path=tmp_path, use_shm=False)
    await commander.initialize()

    # Send 500 tasks to domain 'finance'
    tasks = [{"domain": "finance", "id": i} for i in range(500)]
    async with commander.strike_mode("finance"):
        await commander.execute_global_dispatch(tasks)

    report = await commander.get_density_report()
    assert report["legions"] == 1
    # 500 tasks, each agent handles 1 task.
    # 500 agents require 5 centurions (cap 100)
    assert report["centurions"] == 5
    assert report["agents"] == 500

    await commander.consolidate_and_annihilate()
    # Check teardown
    assert len(commander.legions) == 0


@pytest.mark.asyncio
async def test_swarm_commander_fallback_uses_directory_for_file_bus_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Fallback to the sharded bus should not try to mkdir over a DB file path."""
    db_file = tmp_path / "cortex.db"
    db_file.write_text("")

    class BrokenSharedBus:
        def __init__(self, *args, **kwargs) -> None:
            raise PermissionError("shared memory unavailable")

    monkeypatch.setattr("cortex.engine.swarm_10k.SovereignSharedBus", BrokenSharedBus)

    commander = SwarmCommander(bus_path=db_file, use_shm=True)
    await commander.initialize()

    shard_dir = tmp_path / "cortex.db.shards"
    assert shard_dir.is_dir()
    assert (shard_dir / "swarm_shard_000.db").exists()

    await commander.consolidate_and_annihilate()


@pytest.mark.asyncio
async def test_swarm_commander_batched_dispatch_rejects_invalid_batch_size(tmp_path: Path):
    """Batched dispatch should fail fast on invalid batch sizes."""
    commander = SwarmCommander(bus_path=tmp_path, use_shm=False)
    await commander.initialize()

    with pytest.raises(ValueError, match="batch_size must be greater than zero"):
        await commander.execute_global_dispatch_batched(
            tasks=[{"domain": "default", "payload": "x"}],
            parallel=True,
            batch_size=0,
        )

    await commander.consolidate_and_annihilate()


@pytest.mark.asyncio
async def test_swarm_commander_uses_configured_legion_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Legion worker and queue sizing should be controlled by config."""
    monkeypatch.setattr(config, "SWARM_LEGION_WORKERS", 3)
    monkeypatch.setattr(config, "SWARM_LEGION_QUEUE_MAXSIZE", 7)

    commander = SwarmCommander(bus_path=tmp_path, use_shm=False)
    legion = await commander.get_or_create_legion("finance")

    assert len(legion._workers) == 3
    assert legion.queue.maxsize == 7

    await commander.consolidate_and_annihilate()
