import pytest
import asyncio
from cortex.engine.mev_telemetry import MEVTelemetryDaemon


@pytest.mark.asyncio
async def test_mev_telemetry_lifecycle():
    daemon = MEVTelemetryDaemon(interval_seconds=0.1)
    assert not daemon.is_running

    await daemon.start()
    assert daemon.is_running

    # Permitir una iteración del daemon
    await asyncio.sleep(0.15)

    assert daemon.metrics["total_liquidations_scanned"] > 0

    daemon.report_violation("tx_0xdeadbeef", 420.69)
    assert daemon.metrics["ceil_division_bypasses_detected"] == 1
    assert daemon.metrics["truncation_mev_leakage_usd"] == 420.69

    await daemon.stop()
    assert not daemon.is_running
