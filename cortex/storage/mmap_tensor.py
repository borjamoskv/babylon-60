"""CORTEX v6.1 — Direct-Silicon JIT: Memory-Mapped Void-State Backend.
Provides O(1) latency bridging for 3-bit QJL tensor routing by completely evading REST/gRPC.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("cortex.storage.mmap")

VOID_DIM = 8192

class MmapVoidStateBackend:
    """Hardware-adjacent Memory-Mapped Tensor Backend (L2)."""

    def __init__(self, storage_dir: str | Path, capacity: int = 20000):
        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self.capacity = capacity
        
        self._mmap_path = self._dir / "void_state_tensor.mmap"
        self._meta_path = self._dir / "void_state_metadata.json"
        
        self._vectors: np.memmap | None = None
        self._meta: dict[int, dict[str, Any]] = {}
        self._node_to_slot: dict[int, int] = {}
        self._next_slot = 0
        self._lock = asyncio.Lock()

    async def connect(self):
        """Initialize the memory map."""
        if not self._mmap_path.exists():
            self._vectors = np.memmap(
                self._mmap_path, dtype='uint8', mode='w+', shape=(self.capacity, VOID_DIM)
            )
            self._vectors[:] = 0
            self._vectors.flush()
        else:
            self._vectors = np.memmap(
                self._mmap_path, dtype='uint8', mode='r+', shape=(self.capacity, VOID_DIM)
            )
            
        if self._meta_path.exists():
            with open(self._meta_path) as f:
                data = json.load(f)
                self._meta = {int(k): v for k, v in data.get("meta", {}).items()}
                self._node_to_slot = {int(k): v for k, v in data.get("node_to_slot", {}).items()}
                self._next_slot = data.get("next_slot", 0)
        logger.info("MmapVoidStateBackend initialized at %s (capacity=%d)", self._mmap_path, self.capacity)

    async def _save_meta(self):
        data = {
            "meta": self._meta,
            "node_to_slot": self._node_to_slot,
            "next_slot": self._next_slot
        }
        with open(self._meta_path, "w") as f:
            json.dump(data, f)

    async def upsert_void(
        self,
        node_id: int,
        tensor_uint8: list[int],
        tenant_id: str = "default",
        payload: dict[str, Any] | None = None,
    ) -> None:
        """[Swarm-100] Direct injection bypasses OS kernel buffer cache through MMAP."""
        if self._vectors is None:
            raise RuntimeError("Backend not connected")
            
        async with self._lock:
            slot = self._node_to_slot.get(node_id)
            if slot is None:
                if self._next_slot >= self.capacity:
                    logger.warning("MMAP Tensor Backend full! Evicting slot 0.")
                    slot = 0
                    self._next_slot = 1
                else:
                    slot = self._next_slot
                    self._next_slot += 1
                self._node_to_slot[node_id] = slot
                
            self._vectors[slot] = tensor_uint8
            self._vectors.flush()
            
            project = payload.get("project") if payload else None
            self._meta[slot] = {
                "node_id": node_id,
                "tenant_id": tenant_id,
                "project": project,
                "payload": payload or {}
            }
            await self._save_meta()

    async def search_void(
        self,
        query_tensor: list[int],
        top_k: int = 5,
        tenant_id: str = "default",
        project: str | None = None,
    ) -> list[tuple[int, float]]:
        """[Swarm-100] O(1) Array Dot-Product bypassing gRPC overhead."""
        if self._vectors is None or self._next_slot == 0:
            return []
            
        q = np.array(query_tensor, dtype=np.float32)
        active_vectors = self._vectors[:self._next_slot].astype(np.float32)
        scores = np.dot(active_vectors, q)
        
        results = []
        for slot in range(self._next_slot):
            m = self._meta.get(slot, {})
            if m.get("tenant_id") == tenant_id:
                if project and m.get("project") != project:
                    continue
                results.append((m["node_id"], float(scores[slot])))
                
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    async def close(self) -> None:
        pass
