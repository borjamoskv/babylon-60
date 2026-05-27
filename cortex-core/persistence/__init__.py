import sys
from pathlib import Path

from .base import (
    SovereignResource,
    _setup_sqlite_pragmas,
    DB_PATH,
    VSA_BIN_PATH,
    VSA_DIMENSION,
    HAS_CORTEX_RS,
    outbox_wake_event,
    ledger_entropy_event,
    _get_local_conn,
    logger,
    _metrics_cache,
    _metrics_cache_lock,
)
from .cache import ContextCache
from .ledger import LedgerManager
from .vsa import VSAMemory
from .ide_preserver import IdeStatePreserver
from .hybrid import HybridPersistenceManager

# Lazy import: UltramapSubstrate lives one level up, resolve without sys.path mutation
_ultramap_parent = str(Path(__file__).resolve().parent.parent)
if _ultramap_parent not in sys.path:
    sys.path.insert(0, _ultramap_parent)
from ultramap import UltramapSubstrate

# Lazy imports to avoid circular dependencies
def __getattr__(name):
    if name in ("outbox", "ZeroCopyRingBuffer", "OutboxDaemon", "enqueue_swarm_task", 
                "get_swarm_metrics", "_get_ring_buffer"):
        import daemons.outbox as outbox_module
        sys.modules["persistence.outbox"] = outbox_module
        globals().update({
            "outbox": outbox_module,
            "ZeroCopyRingBuffer": outbox_module.ZeroCopyRingBuffer,
            "OutboxDaemon": outbox_module.OutboxDaemon,
            "enqueue_swarm_task": outbox_module.enqueue_swarm_task,
            "get_swarm_metrics": outbox_module.get_swarm_metrics,
            "_get_ring_buffer": outbox_module._get_ring_buffer,
        })
        return globals()[name]
    if name in ("security_recon", "SecurityReconDaemon"):
        import daemons.security_recon as recon_module
        sys.modules["persistence.security_recon"] = recon_module
        globals().update({
            "security_recon": recon_module,
            "SecurityReconDaemon": recon_module.SecurityReconDaemon,
        })
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "SovereignResource",
    "_setup_sqlite_pragmas",
    "DB_PATH",
    "VSA_BIN_PATH",
    "VSA_DIMENSION",
    "HAS_CORTEX_RS",
    "outbox_wake_event",
    "ledger_entropy_event",
    "_get_local_conn",
    "logger",
    "ContextCache",
    "LedgerManager",
    "VSAMemory",
    "ZeroCopyRingBuffer",
    "OutboxDaemon",
    "enqueue_swarm_task",
    "get_swarm_metrics",
    "IdeStatePreserver",
    "SecurityReconDaemon",
    "HybridPersistenceManager",
    "_metrics_cache",
    "_metrics_cache_lock",
    "_get_ring_buffer",
    "UltramapSubstrate",
    "outbox",
    "security_recon",
]
