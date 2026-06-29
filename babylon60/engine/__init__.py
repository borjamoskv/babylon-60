# CORTEX ENGINE FACADE
# Auto-generated to maintain compatibility after structural mitosis.

_SWARM_MODULES = {
    "agent_mixin",
    "aleph_omega",
    "auth",
    "auth_gateway",
    "autocurative_agent",
    "autopoietic_agent",
    "enrichment_worker",
    "entropy_daemon",
    "exergy_agent",
    "exergy_daemon",
    "legion",
    "legion_vectors",
    "legion_vectors_plan",
    "nemesis_agent",
    "omega_daemon",
    "phoenix_omega",
    "squadrons",
    "swarm_10k",
    "test_autopoietic_agent",
    "trust_registry",
}

_DEFERRED_ATTRIBUTES = {
    "AsyncCortexEngine": ".core.cortex_engine",
    "CortexEngine": ".core.cortex_engine",
}

def __getattr__(name: str):
    if name in _SWARM_MODULES:
        import importlib
        return importlib.import_module(f"cortex.swarm.{name}")
    if name in _DEFERRED_ATTRIBUTES:
        import importlib
        mod = importlib.import_module(_DEFERRED_ATTRIBUTES[name], __name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __dir__():
    return sorted(list(globals().keys()) + list(_SWARM_MODULES) + list(_DEFERRED_ATTRIBUTES.keys()))


from .core import (
    _engine_connection as _engine_connection,
    _engine_delegates as _engine_delegates,
    bifurcation_engine as bifurcation_engine,
    context_cache as context_cache,
    distributed_ledger as distributed_ledger,
    embedding_engine as embedding_engine,
    engine as engine,
    evolution_engine as evolution_engine,
    evolution_ledger as evolution_ledger,
    fact_store_core as fact_store_core,
    memory_mixin as memory_mixin,
    mutation_engine as mutation_engine,
    physics as physics,
    rollback_engine as rollback_engine,
    runtime_kernel as runtime_kernel,
    snapshots as snapshots,
    store_mixin as store_mixin,
    store_mutation as store_mutation,
    store_quarantine_mixin as store_quarantine_mixin,
    store_validation as store_validation,
    store_validators as store_validators,
    tips as tips,
    tuning_store as tuning_store,
    ultrathink_physics as ultrathink_physics,
)
from .evo import (
    _autocurative_config as _autocurative_config,
    _autocurative_helper as _autocurative_helper,
    _autocurative_state as _autocurative_state,
    _autopoietic_helper as _autopoietic_helper,
    _autopoietic_state as _autopoietic_state,
    _genome_mutator as _genome_mutator,
    _genome_tree_helper as _genome_tree_helper,
    _genome_types as _genome_types,
    _mutation_projectors as _mutation_projectors,
    autopoiesis as autopoiesis,
    decalcifier as decalcifier,
    evaporator as evaporator,
    evolution_metrics as evolution_metrics,
    evolution_types as evolution_types,
    genome as genome,
    growth as growth,
    healing_stack as healing_stack,
    reaper as reaper,
    repair_strategies as repair_strategies,
)
from .flow import (
    arbiter_bridge as arbiter_bridge,
    bridge_guard as bridge_guard,
    cascade_router as cascade_router,
    causal_scheduler as causal_scheduler,
    causality as causality,
    causality_models as causality_models,
    checkpoint as checkpoint,
    consensus as consensus,
    encb_router as encb_router,
    execution_ledger as execution_ledger,
    guard_adapters as guard_adapters,
    guard_integration_patch as guard_integration_patch,
    guard_pipeline as guard_pipeline,
    lock as lock,
    rim_latent_blocks as rim_latent_blocks,
    saga_protocol as saga_protocol,
    storage_guard as storage_guard,
)
from .meta import (
    _autopoietic_oracle as _autopoietic_oracle,
    cognitive as cognitive,
    cognitive_arbiter as cognitive_arbiter,
    forgetting_oracle as forgetting_oracle,
    meta_arbiter as meta_arbiter,
    meta_arbiter_kernel as meta_arbiter_kernel,
    meta_arbiter_types as meta_arbiter_types,
    metabolism as metabolism,
    metacognition as metacognition,
    metadata_engine as metadata_engine,
    nemesis as nemesis,
    psychology as psychology,
    right_brain as right_brain,
    sovereign_arbiter as sovereign_arbiter,
    vision_reasoner as vision_reasoner,
)
