
import sys
import os
from pathlib import Path

# Ensure sibling packages are reachable
_core_dir = str(Path(__file__).resolve().parent.parent)
if _core_dir not in sys.path:
    sys.path.insert(0, _core_dir)

from ultramap import UltramapSubstrate

from .base import DB_PATH



from .cache import ContextCache
from .vsa import VSAMemory
from .ledger import LedgerManager
from daemons.outbox import ZeroCopyRingBuffer, OutboxDaemon
from .ide_preserver import IdeStatePreserver
from daemons.security_recon import SecurityReconDaemon


class HybridPersistenceManager:
    """
    Sovereign Hybrid Persistence Manager.
    Integrates L1 (RAM Context), L2 (Semantic VSA/SQLite), L3 (Cryptographic Audit Ledger),
    L4 (Zero-Copy Ring Buffer), and L5 (Topological Space).
    """

    def __init__(self):
        self.l1 = ContextCache()
        self.l2 = VSAMemory()
        self.l3 = LedgerManager()
        self.ring = ZeroCopyRingBuffer()  # L4 Zero-Copy Substrate
        self.ultramap = UltramapSubstrate()  # L5 Sovereign Topological Space
        self.ide_guardian = IdeStatePreserver(self.l3)
        self.outbox = OutboxDaemon(DB_PATH, ledger=self.l3)
        self.security_radar = SecurityReconDaemon(self.l3)
        self.ide_guardian.start_guardian()
        self.outbox.start_guardian()
        self.security_radar.start_guardian()

    def get_system_health(self) -> dict:
        """Aggregates C5-REAL telemetry from all persistence substrates."""
        ring_pending = self.ring.get_pending_count()
        return {
            "outbox": self.outbox.get_health_metrics(),
            "ledger_yield": self.l3.get_total_yield(),
            "ring_pending": ring_pending,
            "l1_cache_size": len(self.l1),
            "status": "C5-REAL_OPERATIONAL",
        }
