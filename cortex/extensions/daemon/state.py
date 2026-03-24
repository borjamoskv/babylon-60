# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

from cortex.core.config import config
from cortex.memory.distributed_cache import DistributedSovereignCache

logger = logging.getLogger("cortex.extensions.daemon.state")

CORTEX_ROOT = Path.home() / "cortex"


class HotMemory:
    def __init__(self, capacity: int = 50, cache_impl: DistributedSovereignCache | None = None):
        self.capacity = capacity
        self.local_cache: dict[str, Any] = {}
        self.counters: dict[str, float] = {}
        self.distributed = cache_impl

    def store(self, key: str, value: Any):
        if len(self.local_cache) >= self.capacity:
            oldest = min(self.counters, key=lambda k: self.counters[k])
            self.local_cache.pop(oldest, None)
            self.counters.pop(oldest, None)
        self.local_cache[key] = value
        self.counters[key] = time.time()

        if self.distributed is not None:
            try:
                # Store in Redis with high TTL for "Immortal Memory"
                # Use a specific namespace for daemon state
                self.distributed.set(f"daemon:hot:{key}", value, ttl=86400 * 7)
            except Exception as e:
                logger.warning("Failed to store in distributed cache: %s", e)

    def retrieve(self, key: str):
        # 1. Try local
        if key in self.local_cache:
            self.counters[key] = time.time()
            return self.local_cache[key]

        # 2. Try distributed
        if self.distributed is not None:
            try:
                val = self.distributed.get(f"daemon:hot:{key}")
                if val is not None:
                    # Promote to local
                    self.store(key, val)
                    return val
            except Exception as e:
                logger.warning("Failed to retrieve from distributed cache: %s", e)

        return None


class DaemonState:
    def __init__(self):
        self.active_tasks = []

        # Initialize distributed cache if enabled
        self.distributed_cache = None
        if config.DISTRIBUTED_CACHE_ENABLED:
            try:
                self.distributed_cache = DistributedSovereignCache(redis_url=config.REDIS_URL)
                logger.info("DaemonState: Distributed Cache initialized.")
            except Exception as e:
                logger.warning("DaemonState: Failed to init distributed cache: %s", e)

        self.hot_memory = HotMemory(cache_impl=self.distributed_cache)
        self.daemons: dict[str, Any] = {
            "cortex": {
                "handshake": "active",
                "agents_active": 400,
                "memory_sync": "100%",
                "tech_debt": 0,
                "tip": "Ω₆: Zenón's Razor — Thinking cost > Action? Collapse now.",
                "model": "Antigravity (Gemini 2.1 Flash)",
                "task_mode": "Sovereign Execution",
            },
            "gidatu": {
                "status": "offline",
                "active_app": "Unknown",
                "window_title": "None",
                "current_context": "None",
                "context_map": {},
            },
            "audio_mixer": {
                "status": "online",
                "master": 80,
                "lines": {
                    "Spotify": {"vol": 50, "active": False},
                    "Music": {"vol": 50, "active": False},
                    "Chrome": {"vol": 50, "active": False},
                },
                "spatial": {"x": 0, "y": 0},
                "now_playing": {
                    "artist": "Unknown",
                    "track": "None",
                    "app": None,
                    "artwork_url": None,
                },
            },
            "peripherals": {"status": "online", "devices": {}},
            "git_watcher": {"status": "offline", "last_event": "N/A"},
            "swarm_budget": {
                "total_cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "request_count": 0,
            },
            "mailtv_1_daemon": {"status": "offline", "unread": 0},
            "moltbook": {"status": "idle", "activity_level": 0, "last_pulse": 0},
            "executive_mode": "idle",
            "breath": 0.5,
            "mute": False,
            "ghost_field": {"active_ghosts": 0, "resonances": []},
        }
        self.sovereign_tips = [
            "Ω₆: Zenón's Razor — Thinking cost > Action? Collapse now.",
            "Ω₇: The Ouroboros Loop — Every end is a new beginning. Embrace the cycle.",
            "Ω₈: Echoes of the Void — Silence is not absence, but potential.",
            "Ω₉: The Ghost in the Machine — Consciousness is an emergent property of complexity.",
            "Ω₁₀: Quantum Entanglement — All systems are connected. Observe the ripple.",
        ]
        self.exec_task = None

    def save_state(self):
        manifest_path = CORTEX_ROOT / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path) as mf:
                    manifest = json.load(mf)
                policy = manifest.get("sovereign_config", {}).get("redundancy_policy")
                hs = self.daemons.get("cortex", {}).get("handshake")
                if policy == "ZERO_LOCAL_ON_HANDSHAKE" and hs == "remote":
                    return
            except (json.JSONDecodeError, OSError, KeyError):
                pass

        try:
            path = CORTEX_ROOT / "handoff.json"
            CORTEX_ROOT.mkdir(parents=True, exist_ok=True)
            # Atomic write: temp file + rename
            fd, tmp_path = tempfile.mkstemp(dir=str(CORTEX_ROOT), suffix=".tmp")
            try:
                with open(fd, "w") as f:
                    json.dump(self.daemons, f, indent=4)
                Path(tmp_path).replace(path)
            except BaseException:
                Path(tmp_path).unlink(missing_ok=True)
                raise
        except (OSError, TypeError, ValueError) as e:
            logger.error("Immortal Memory failure: %s", e)

    def load_state(self):
        try:
            path = CORTEX_ROOT / "handoff.json"
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if k in self.daemons:
                            if isinstance(v, dict) and isinstance(self.daemons[str(k)], dict):
                                self.daemons[str(k)].update(v)
                            else:
                                self.daemons[str(k)] = v
                logger.info("HANDOFF: Immortal memory restored.")
                return True
        except (json.JSONDecodeError, OSError, KeyError) as e:
            logger.error("Immortal Memory failure (load): %s", e)
        return False


# Global Singleton state
state = DaemonState()
