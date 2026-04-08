from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from cortex.extensions.hypervisor.core import AgencyHypervisor
from cortex.extensions.hypervisor.projector import EventProjector


@pytest.mark.asyncio
async def test_hypervisor_reflect_marks_failed_stats_as_unverified(caplog) -> None:
    engine = AsyncMock()
    engine.recall.side_effect = RuntimeError("stats unavailable")
    engine.verify_ledger.return_value = {"valid": True}

    hypervisor = AgencyHypervisor(engine)
    hypervisor.create_handle("tenant-a", "proj-a")

    with caplog.at_level("WARNING"):
        report = await hypervisor._do_reflect(tenant="tenant-a", project="proj-a")

    assert report.status == "critical"
    assert report.integrity == "unverified"
    assert any("failed to gather stats" in msg for msg in caplog.messages)


@pytest.mark.asyncio
async def test_event_projector_logs_recall_side_effect_failures(monkeypatch, caplog) -> None:
    projector = EventProjector(AsyncMock())

    async def _boom(*args, **kwargs):
        raise RuntimeError("endocrine offline")

    monkeypatch.setattr(EventProjector, "_signal_endocrine", _boom)

    with caplog.at_level("DEBUG"):
        await projector.on_recall("query", "proj-a")

    assert any("on_recall endocrine signal failed" in msg for msg in caplog.messages)
