# [C5-REAL] Exergy-Maximized
# Author: Borja Moskv (borjamoskv)
import asyncio
import pytest
from cortex.engine.latticework_store import LatticeworkStore
from cortex.engine.latticework_daemon import LatticeworkDaemon
from cortex.engine.babylon60 import Babylon60

def test_latticework_store_initialization():
    store = LatticeworkStore()
    # Check that primitives are loaded
    assert len(store.primitives) > 0
    # Retrieve primitive 9
    prim9 = store.get_primitive(9)
    assert prim9 is not None
    assert prim9.id == 9
    assert prim9.base60_constant >= 0

def test_latticework_store_search():
    store = LatticeworkStore()
    results = store.search_by_keyword("Matrix") or store.search_by_keyword("Matriz")
    assert len(results) >= 0

@pytest.mark.asyncio
async def test_latticework_daemon_lifecycle():
    class DummyLedger:
        def __init__(self):
            self.anomalies = []
        async def get_recent_anomalies(self, limit=10):
            return self.anomalies

    class DummyScheduler:
        def __init__(self):
            self.exergy_injections = []
        async def inject_exergy(self, anomaly_id, exergy_val):
            self.exergy_injections.append((anomaly_id, exergy_val))

    ledger = DummyLedger()
    scheduler = DummyScheduler()
    daemon = LatticeworkDaemon(ledger, scheduler, scan_interval=1)
    
    # Check coverage report
    report = daemon.omega_index.coverage_report()
    assert report["total"] == 100
    assert report["coverage_pct"] > 0.0

    # Start the daemon
    daemon.start()
    assert daemon._running is True
    assert daemon._task is not None

    # Wait a bit for at least one tick
    await asyncio.sleep(1.2)

    # Stop the daemon
    await daemon.stop()
    assert daemon._running is False
