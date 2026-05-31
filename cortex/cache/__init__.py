"""CORTEX Cache - Distributed Working Memory."""

from cortex.cache.redis_l1 import HAS_REDIS, RedisL1Cache

__all__ = ["HAS_REDIS", "RedisL1Cache"]
