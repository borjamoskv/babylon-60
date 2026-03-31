"""L1 Working Memory & Swarm Bus via Redis."""

import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional

import msgpack
import redis.asyncio as redis

logger = logging.getLogger("cortex.storage.redis_bus")


class RedisBus:
    """L1 distributed cache and event bus for Sovereign Swarm."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._redis: Optional[redis.Redis] = None

    async def connect(self):
        """Establish connection to Redis."""
        self._redis = redis.from_url(self._dsn, decode_responses=False)
        await self._redis.ping()
        logger.info("Connected to Redis Swarm Bus (MsgPack Binary)")

    async def disconnect(self):
        """Close connection to Redis."""
        if self._redis:
            await self._redis.aclose()

    async def set_context(self, tenant_id: str, key: str, value: Any, ttl: int = 3600):
        """Set an ephemeral working memory key with TTL."""
        if not self._redis:
            raise RuntimeError("RedisBus not connected")
        full_key = f"tenant:{tenant_id}:{key}"
        await self._redis.setex(full_key, ttl, msgpack.packb(value))

    async def get_context(self, tenant_id: str, key: str) -> Optional[Any]:
        """Retrieve an ephemeral working memory key."""
        if not self._redis:
            raise RuntimeError("RedisBus not connected")
        full_key = f"tenant:{tenant_id}:{key}"
        data = await self._redis.get(full_key)
        return msgpack.unpackb(data, strict_map_key=False) if data else None

    async def set_raw_tensor(self, tenant_id: str, key: str, tensor: bytes, ttl: int = 3600):
        """[Swarm-100] Set binary 3-bit KV-cache directly evading JSON limits."""
        if not self._redis:
            raise RuntimeError("RedisBus not connected")
        full_key = f"tenant:{tenant_id}:tensor:{key}"
        await self._redis.setex(full_key, ttl, tensor)

    async def get_raw_tensor(self, tenant_id: str, key: str) -> Optional[bytes]:
        """[Swarm-100] Retrieve raw binary Tensor payload for instant Swarm context swap."""
        if not self._redis:
            raise RuntimeError("RedisBus not connected")
        full_key = f"tenant:{tenant_id}:tensor:{key}"
        return await self._redis.get(full_key)

    async def publish(self, channel: str, message: dict[str, Any]):
        """Publish an event to the Distributed Event Bus."""
        if not self._redis:
            raise RuntimeError("RedisBus not connected")
        await self._redis.publish(channel, msgpack.packb(message))

    async def subscribe(self, channel: str) -> AsyncGenerator[dict[str, Any], None]:
        """Subscribe to a channel and yield messages asynchronously."""
        if not self._redis:
            raise RuntimeError("RedisBus not connected")
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield msgpack.unpackb(message["data"], strict_map_key=False)
