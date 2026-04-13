from __future__ import annotations

import pytest

from cortex.extensions.swarm.conflict_resolution import (
    AgentProfile,
    ConflictOption,
    ConflictResolver,
    ConflictType,
    ResolutionMethod,
)


def _option(option_id: str) -> ConflictOption:
    return ConflictOption(
        id=option_id,
        description=f"Option {option_id}",
        proposer_id=f"agent:{option_id}",
        confidence=0.7,
        reversibility=0.5,
        estimated_cost=10.0,
    )


@pytest.mark.asyncio
async def test_factual_conflict_without_valid_votes_escalates() -> None:
    resolver = ConflictResolver()

    record = await resolver.resolve(
        conflict_type=ConflictType.FACTUAL,
        options=[_option("alpha"), _option("beta")],
        agents={
            "agent-1": (AgentProfile(agent_id="agent-1"), "unknown-option"),
            "agent-2": (AgentProfile(agent_id="agent-2"), "still-unknown"),
        },
    )

    assert record.resolution.method == ResolutionMethod.HUMAN_ESCALATION
    assert record.resolution.winner_id == ""
    assert record.resolution.consensus_level == 0.0
    assert "escalation required" in record.resolution.reasoning.lower()


@pytest.mark.asyncio
async def test_factual_conflict_with_valid_votes_uses_triangulation() -> None:
    resolver = ConflictResolver()

    record = await resolver.resolve(
        conflict_type=ConflictType.FACTUAL,
        options=[_option("alpha"), _option("beta")],
        agents={
            "agent-1": (AgentProfile(agent_id="agent-1"), "beta"),
            "agent-2": (AgentProfile(agent_id="agent-2"), "beta"),
            "agent-3": (AgentProfile(agent_id="agent-3"), "alpha"),
        },
    )

    assert record.resolution.method == ResolutionMethod.TRIANGULATION
    assert record.resolution.winner_id == "beta"
    assert record.resolution.consensus_level == pytest.approx(2 / 3)
