"""Tests for KV Prefix Registry ensuring Tenant Isolation."""

from cortex.extensions.swarm.kv_prefix_registry import KVPrefixRegistry


def test_tenant_isolation_invariants():
    registry = KVPrefixRegistry()

    system_prompt = "You are a helpful assistant for the CORTEX swarm."

    # Register under tenant A
    slot_a = registry.register(
        mission_id="mission-123",
        tenant_id="tenant-A",
        system_prompt=system_prompt,
        provider_name="gemini",
        model_name="gemini-1.5-pro",
    )

    # Register under tenant B (same mission, same prompt - edge case/malicious)
    slot_b = registry.register(
        mission_id="mission-123",
        tenant_id="tenant-B",
        system_prompt=system_prompt,
        provider_name="google",
        model_name="gemini-1.5-flash",
    )

    # 1. Cache keys MUST be different
    assert slot_a.cache_key != slot_b.cache_key

    # 2. Retrieval checks
    retrieved_a = registry.get_slot("mission-123", "tenant-A", system_prompt)
    assert retrieved_a is not None
    assert retrieved_a.cache_key == slot_a.cache_key
    assert retrieved_a.hits == 1

    # Attempt cross-tenant retrieval
    retrieved_cross = registry.get_slot("mission-123", "tenant-B", system_prompt)
    assert retrieved_cross is not None
    assert retrieved_cross.cache_key == slot_b.cache_key
    assert retrieved_cross.cache_key != slot_a.cache_key


def test_exergy_tracking():
    registry = KVPrefixRegistry()
    sys_prompt = "word " * 100  # ~100 tokens approx

    registry.register("m-1", "t-1", sys_prompt, "gemini", "gemini-1.5-pro")
    registry.get_slot("m-1", "t-1", sys_prompt)
    registry.get_slot("m-1", "t-1", sys_prompt)

    report = registry.exergy_report()
    assert report["total_slots"] == 1


def test_lazy_ttl_eviction():
    registry = KVPrefixRegistry()
    sys_prompt = "TTL decay simulation"
    # Registrar un nodo que caduca en -10 segundos (ya nació caducado)
    slot = registry.register("m-1", "t-1", sys_prompt, "anthropic", "claude-3-opus", ttl_seconds=-10)
    
    # El diccionario de raw slots aún lo tiene antes de evaluarlo
    assert slot.cache_key in registry._slots

    # Al evaluar cache affinity, el sistema debe detectarlo como expirado y purgarlo
    active_providers = registry.check_cache_affinity(sys_prompt)
    
    # Afinidad debe estar muerta
    assert len(active_providers) == 0
    # Lazy Eviction debe haber aniquilado el slot
    assert slot.cache_key not in registry._slots

