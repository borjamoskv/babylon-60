from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.extensions.red_team.hydra_chaos import MockRedisClient
from cortex.memory.distributed_cache import DistributedSovereignCache


@pytest.mark.asyncio
async def test_distributed_cache_get_rejects_stale_shadow_after_trigger_expiry() -> None:
    redis = MockRedisClient()
    cache = DistributedSovereignCache(redis)

    await cache.put("agent:test", {"v": 1}, ttl=60)
    await redis.delete("cortex:trigger:agent:test")

    assert await cache.get("agent:test") is None


@pytest.mark.asyncio
async def test_handoff_preserves_shadow_when_chain_advance_fails(monkeypatch) -> None:
    redis = MockRedisClient()
    cache = DistributedSovereignCache(redis)

    shadow_key = "cortex:shadow:agent:test"
    trigger_key = "cortex:trigger:agent:test"
    await redis.set(shadow_key, '{"v": 1}')
    await redis.set(trigger_key, "1")

    async def _failed_advance(*args, **kwargs):
        return {"error": "stream unavailable", "event": "EVICTION_DEGRADED"}

    class _PubSub:
        psubscribe = AsyncMock()
        unsubscribe = AsyncMock()
        aclose = AsyncMock()

        async def listen(self):
            yield {"type": "pmessage", "data": trigger_key}

    monkeypatch.setattr(cache, "_reliable_advance_chain", _failed_advance)
    redis.pubsub = MagicMock(return_value=_PubSub())

    await cache._handoff_loop()

    assert await redis.get(shadow_key) == '{"v": 1}'


@pytest.mark.asyncio
async def test_stream_consumer_does_not_start_without_audit_callback() -> None:
    redis = MockRedisClient()
    cache = DistributedSovereignCache(redis)

    await cache._start_stream_consumer()

    assert cache._consumer_task is None
