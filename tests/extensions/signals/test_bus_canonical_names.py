from __future__ import annotations

from cortex.extensions.signals import AsyncDurableSignalBus, DurableSignalBus
from cortex.extensions.signals.bus import AsyncSignalBus, SignalBus
from cortex.extensions.signals.sharded_bus import ShardedAsyncSignalBus, ShardedDurableSignalBus


def test_durable_signal_bus_legacy_names_are_aliases() -> None:
    assert SignalBus is DurableSignalBus
    assert AsyncSignalBus is AsyncDurableSignalBus


def test_sharded_signal_bus_legacy_name_is_alias() -> None:
    assert ShardedAsyncSignalBus is ShardedDurableSignalBus
