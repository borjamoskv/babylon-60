"""
KV Prefix Registry para SwarmManager.
Implementa RadixAttention-style prefix sharing a nivel de aplicación.
AX-042 compliance: elimina recompute de system_prompt por agente.
AGENTS.md Tenant Isolation: cache_key siempre incluye tenant_id.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
import time


import json

@lru_cache(maxsize=1024)
def _hash_string_sha3_256(content: str) -> str:
    """Cache-backed sha3_256 for identical scalar strings."""
    return hashlib.sha3_256(content.encode('utf-8')).hexdigest()

def hash_prompt(system_prompt: str, episodic_context: list[dict] | None = None) -> str:
    """O(1) SHA3-256 Hybrid Hashing para prompts y payloads multimodales.
    
    Implementación asimétrica: el `system_prompt` (largo) se memoiza,
    y el `episodic_context` se acumula incrementalmente, evitando rehashing
    completo si cambia solo un frame.
    """
    base_hash = _hash_string_sha3_256(system_prompt)
    
    if not episodic_context:
        return base_hash
        
    # Asymmetric incremental hashing
    h = hashlib.sha3_256(base_hash.encode('utf-8'))
    for item in episodic_context:
        item_str = json.dumps(item, sort_keys=True)
        h.update(item_str.encode('utf-8'))
        
    return h.hexdigest()


@dataclass
class PrefixSlot:
    """Un slot de KV prefix compartido entre agentes del mismo mission."""
    mission_id: str
    tenant_id: str
    prefix_hash: str          # sha256 del system_prompt
    prefix_tokens: int        # longitud del prefix
    provider_name: str        # Proveedor físico donde reside el prefix (EJ: 'gemini', 'anthropic')
    model_name: str           # Modelo físico (EJ: 'gemini-1.5-pro')
    ttl_seconds: int = 3600
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: float = field(default_factory=lambda: time.time() + 3600.0)
    hits: int = 0             # agentes que reutilizaron este slot

    @property
    def cache_key(self) -> str:
        """Tenant-scoped cache key. NEVER expose cross-tenant."""
        return hashlib.sha256(
            f"{self.tenant_id}:{self.mission_id}:{self.prefix_hash}".encode()
        ).hexdigest()


class KVPrefixRegistry:
    """
    Application-level registry for tracking and safely sharing 
    KV cache slots across multiple orchestrator missions running 
    in the same process, enforcing tenant isolation (AX-042).
    """

    def __init__(self) -> None:
        self._slots: dict[str, PrefixSlot] = {}  # cache_key → slot
        self._prefix_providers: dict[str, set[str]] = {}  # prefix_hash → set of provider_names
        self._savings_tokens: int = 0
        self._prefill_locks: dict[str, asyncio.Event] = {}  # prefix_hash -> Event

    def register(
        self,
        mission_id: str,
        tenant_id: str,
        system_prompt: str,
        provider_name: str,
        model_name: str,
        ttl_seconds: int = 3600,
        episodic_context: list[dict] | None = None,
    ) -> PrefixSlot:
        """Registra un nuevo prefix slot para una misión."""
        prefix_hash = hash_prompt(system_prompt, episodic_context)
        slot = PrefixSlot(
            mission_id=mission_id,
            tenant_id=tenant_id,
            prefix_hash=prefix_hash,
            prefix_tokens=len(system_prompt.split()),  # approx estimation
            provider_name=provider_name,
            model_name=model_name,
            ttl_seconds=ttl_seconds,
            expires_at=time.time() + ttl_seconds,
        )
        self._slots[slot.cache_key] = slot
        
        # O(1) lookup index
        if prefix_hash not in self._prefix_providers:
            self._prefix_providers[prefix_hash] = set()
        self._prefix_providers[prefix_hash].add(slot.cache_key)
        
        return slot

    def get_slot(
        self, 
        mission_id: str, 
        tenant_id: str, 
        system_prompt: str,
        episodic_context: list[dict] | None = None
    ) -> PrefixSlot | None:
        """Recupera slot existente (cache hit) o None (cache miss)."""
        prefix_hash = hash_prompt(system_prompt, episodic_context)
        key = hashlib.sha256(
            f"{tenant_id}:{mission_id}:{prefix_hash}".encode()
        ).hexdigest()
        slot = self._slots.get(key)
        if slot:
            slot.hits += 1
            self._savings_tokens += slot.prefix_tokens
        return slot

    def check_cache_affinity(self, system_prompt: str, episodic_context: list[dict] | None = None) -> list[str]:
        """Returns provider names that have an active cache for this exact prompt hash.
        O(1) Check using dict comprehension and lazy eviction of expired TTL slots.
        """
        prefix_hash = hash_prompt(system_prompt, episodic_context)
        keys = self._prefix_providers.get(prefix_hash, set())
        providers = set()
        now = time.time()
        expired_keys = set()

        for k in keys:
            slot = self._slots.get(k)
            if slot and now < slot.expires_at:
                providers.add(slot.provider_name)
            else:
                expired_keys.add(k)
        
        # Lazy eviction (O(1) cost per expired node)
        if expired_keys:
            self._prefix_providers[prefix_hash].difference_update(expired_keys)
            for k in expired_keys:
                self._slots.pop(k, None)

        return list(providers)

    async def wait_or_acquire_prefill(self, system_prompt: str, episodic_context: list[dict] | None = None) -> bool:
        """
        STAMPEDE MITIGATION: Devuelve True si el agente es el LÍDER y debe recalcular.
        Devuelve False si el agente es FOLLOWER y ha esperado a que el líder termine.
        """
        import asyncio
        prefix_hash = hash_prompt(system_prompt, episodic_context)
        
        if prefix_hash in self._prefill_locks:
            # Somos Follower
            event = self._prefill_locks[prefix_hash]
            await event.wait()
            return False
            
        # Somos Líder
        self._prefill_locks[prefix_hash] = asyncio.Event()
        return True
        
    def release_prefill_lock(self, system_prompt: str, episodic_context: list[dict] | None = None) -> None:
        """Libera a los Follower estancados una vez el Líder inyecta el prefijo en la nube."""
        prefix_hash = hash_prompt(system_prompt, episodic_context)
        event = self._prefill_locks.pop(prefix_hash, None)
        if event:
            event.set()

    def exergy_report(self) -> dict[str, Any]:
        """Informe de exergía recuperada (AX-042)."""
        return {
            "total_slots": len(self._slots),
            "total_hits": sum(s.hits for s in self._slots.values()),
            "tokens_saved": self._savings_tokens,
            "estimated_flops_saved": self._savings_tokens * 4 * 32 * 4096 ** 2,
        }

_registry_key = "__cortex_kv_registry__"

def get_kv_registry() -> KVPrefixRegistry:
    """True singleton provider for KVPrefixRegistry."""
    import sys
    if not hasattr(sys, _registry_key):
        setattr(sys, _registry_key, KVPrefixRegistry())
    return getattr(sys, _registry_key)
