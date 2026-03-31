"""
AX-1000 Integration Test: Leviathan Targeting Engine.
Validates EU AI Act Art. 12 compliance auditing pipeline with
SwarmManager OMEGA dispatch and SovereignLedger persistence.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.engine.nexus.targeting_engine import TargetingEngine
from cortex.swarm.actuators.protocol import ActuatorResponse


@pytest.mark.asyncio
async def test_leviathan_simulated_wave():
    """Without swarm_manager, all targets should be 'simulated'."""
    engine = TargetingEngine()
    results = await engine.execute_swarm_wave()

    assert len(results) == 3
    for r in results:
        assert r.status == "simulated"
        assert r.ledger_committed is False
        assert r.duration_s >= 0
        assert "CORTEX COMPLIANCE AUDIT" in r.report


@pytest.mark.asyncio
async def test_leviathan_omega_dispatch():
    """With a mocked SwarmManager, targets should be 'audited'."""
    mock_engine = MagicMock()
    mock_engine.ledger = MagicMock()
    mock_engine.ledger.record_transaction = AsyncMock()

    mock_swarm = MagicMock()
    mock_swarm.recruit = AsyncMock(return_value=[
        ActuatorResponse(
            content="PR created for compliance integration",
            status="success",
            metadata={"pr_url": "https://github.com/org/repo/pull/42"},
        )
    ])

    engine = TargetingEngine(
        engine=mock_engine,
        swarm_manager=mock_swarm,
    )
    results = await engine.execute_swarm_wave()

    assert len(results) == 3
    for r in results:
        assert r.status == "audited"
        assert r.ledger_committed is True

    # OMEGA should have been dispatched 3 times (one per target)
    assert mock_swarm.recruit.call_count == 3
    for call in mock_swarm.recruit.call_args_list:
        assert call.kwargs["squad_type"] == "OMEGA"
        assert call.kwargs["count"] == 10

    # Ledger should have 3 compliance_audit entries
    assert mock_engine.ledger.record_transaction.call_count == 3
    for call in mock_engine.ledger.record_transaction.call_args_list:
        assert call.kwargs["project"] == "leviathan"
        assert call.kwargs["action"] == "compliance_audit"


@pytest.mark.asyncio
async def test_leviathan_report_content():
    """Compliance reports should contain EU AI Act Art. 12 language."""
    engine = TargetingEngine()
    target = engine.targets[0]
    report = engine.generate_compliance_report(target)

    assert "EU AI Act" in report
    assert "Art. 12" in report
    assert target.name in report
    assert target.jurisdiction in report
    assert "CORTEX Audit Ledger" in report


@pytest.mark.asyncio
async def test_leviathan_discovery_mocked():
    """Dynamic discovery should extend targets list when enabled."""
    engine = TargetingEngine()
    assert len(engine.targets) == 3  # Seed targets only

    # Mock httpx to return a fake EU-based AI agent repo

    async def mock_get(*args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "items": [
                {
                    "full_name": "eu-ai-lab/agent-framework",
                    "name": "agent-framework",
                    "description": "An agentic orchestration framework",
                    "stargazers_count": 500,
                    "owner": {"location": "Berlin, Germany"},
                },
                {
                    "full_name": "us-lab/some-tool",
                    "name": "some-tool",
                    "description": "A tool for something",
                    "stargazers_count": 200,
                    "owner": {"location": "San Francisco"},
                },
            ]
        }
        return resp

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client_instance = AsyncMock()
        mock_client_instance.get = mock_get
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client_instance

        discovered = await engine.discover_targets()

    # Only the Berlin-based repo should be discovered (US one filtered out)
    assert len(discovered) == 1
    assert discovered[0].jurisdiction == "DE"
    assert discovered[0].name == "agent-framework"
    assert discovered[0].sector == "Agentic"
    assert discovered[0].estimated_revenue_usd == 50000.0  # 500 stars * $100


def test_sector_inference():
    """Sector inference should categorize descriptions correctly."""
    assert TargetingEngine._infer_sector("A large language model framework") == "LLM"
    assert TargetingEngine._infer_sector("Computer vision detection pipeline") == "Vision"
    assert TargetingEngine._infer_sector("Multi-agent swarm orchestration") == "Agentic"
    assert TargetingEngine._infer_sector("IoT edge inference engine") == "Edge"
    assert TargetingEngine._infer_sector("Some random project") == "AI/General"

