from __future__ import annotations

from typing import Any, Optional

import pytest

from cortex.composer import (
    APP_FORGE_FACT_TYPE,
    APP_FORGE_SOURCE,
    AppForgeInvocation,
    EngineSovereignStateStore,
    SovereignAppForge,
    SovereignStateEnvelope,
)


def test_state_envelope_generates_verifiable_hash_and_taint() -> None:
    envelope = SovereignStateEnvelope.forge(
        tenant_id="tenant-a",
        project_id="forge-ui",
        app_id="volatility-monitor",
        state_key="filters",
        value={"quote": "USD", "window": "1h"},
        agent_id="forge-agent",
        session_id="runtime:forge-agent",
        version=3,
    )

    assert envelope.verify() is True
    assert '"state_key":"filters"' in envelope.content
    assert envelope.state_hash
    assert envelope.taint.startswith("taint:forge-agent:runtime:forge-agent:")


def test_runtime_contract_and_prompt_use_sovereign_primitives() -> None:
    forge = SovereignAppForge()
    invocation = AppForgeInvocation(
        intent="Real-time volatility monitor for ETH/USD across three DEXs",
        tenant_id="sovereign",
        project_id="markets",
        app_id="dex-monitor",
    )

    contract = forge.runtime_contract_source()
    prompt = forge.system_prompt(invocation)

    assert "useSovereignState" in contract
    assert "useAgentContext" in contract
    assert "generateVectorStream" in contract
    assert "postMessage" in contract
    assert "VSA-SDM" in contract
    assert "Never import Firebase" in prompt
    assert "Intent: Real-time volatility monitor for ETH/USD across three DEXs" in prompt


@pytest.mark.asyncio
async def test_engine_store_round_trip_returns_latest_valid_version() -> None:
    class FakeEngine:
        def __init__(self) -> None:
            self.facts: list[dict[str, Any]] = []

        async def store(self, **kwargs: Any) -> int:
            fact = {
                "id": len(self.facts) + 1,
                "tenant_id": kwargs["tenant_id"],
                "project": kwargs["project"],
                "content": kwargs["content"],
                "fact_type": kwargs["fact_type"],
                "meta": kwargs["meta"],
                "source": kwargs["source"],
            }
            self.facts.append(fact)
            return fact["id"]

        async def get_all_active_facts(
            self,
            tenant_id: str = "default",
            project: Optional[str] = None,
            fact_types: Optional[list[str]] = None,
        ) -> list[dict[str, Any]]:
            allowed = set(fact_types or [])
            return [
                fact
                for fact in self.facts
                if fact["tenant_id"] == tenant_id
                and (project is None or fact["project"] == project)
                and (not allowed or fact["fact_type"] in allowed)
            ]

    engine = FakeEngine()
    store = EngineSovereignStateStore(engine)  # type: ignore[arg-type]

    first = SovereignStateEnvelope.forge(
        tenant_id="tenant-a",
        project_id="forge-ui",
        app_id="volatility-monitor",
        state_key="filters",
        value={"quote": "USD"},
        agent_id="forge-agent",
        session_id="runtime:forge-agent",
        version=1,
    )
    second = SovereignStateEnvelope.forge(
        tenant_id="tenant-a",
        project_id="forge-ui",
        app_id="volatility-monitor",
        state_key="filters",
        value={"quote": "EUR"},
        agent_id="forge-agent",
        session_id="runtime:forge-agent",
        version=2,
    )

    fact_id = await store.write(first)
    await store.write(second)
    latest = await store.read(
        tenant_id="tenant-a",
        project_id="forge-ui",
        app_id="volatility-monitor",
        state_key="filters",
    )

    assert fact_id == 1
    assert latest is not None
    assert latest.value == {"quote": "EUR"}
    assert latest.version == 2
    assert latest.verify() is True
    assert engine.facts[0]["fact_type"] == APP_FORGE_FACT_TYPE
    assert engine.facts[0]["source"] == APP_FORGE_SOURCE


@pytest.mark.asyncio
async def test_engine_store_ignores_tampered_state_records() -> None:
    class FakeEngine:
        def __init__(self, facts: list[dict[str, Any]]) -> None:
            self._facts = facts

        async def get_all_active_facts(
            self,
            tenant_id: str = "default",
            project: Optional[str] = None,
            fact_types: Optional[list[str]] = None,
        ) -> list[dict[str, Any]]:
            return self._facts

    valid = SovereignStateEnvelope.forge(
        tenant_id="tenant-a",
        project_id="forge-ui",
        app_id="dex-monitor",
        state_key="layout",
        value={"view": "chart"},
        agent_id="forge-agent",
        session_id="runtime:forge-agent",
        version=1,
    )
    tampered = {
        "id": 2,
        "tenant_id": "tenant-a",
        "project": "forge-ui",
        "content": valid.content.replace("chart", "table"),
        "fact_type": APP_FORGE_FACT_TYPE,
        "meta": valid.to_fact_meta(),
    }

    store = EngineSovereignStateStore(FakeEngine([tampered]))  # type: ignore[arg-type]
    latest = await store.read(
        tenant_id="tenant-a",
        project_id="forge-ui",
        app_id="dex-monitor",
        state_key="layout",
    )

    assert latest is None
