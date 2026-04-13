from __future__ import annotations

from typing import Any, Protocol

from cortex.engine.models import Fact
from cortex.types.models import VoteResponse


class FactVoteNotFoundError(LookupError):
    """Raised when a vote targets a fact that does not exist for the tenant."""

    def __init__(self, fact_id: int) -> None:
        super().__init__(f"Fact #{fact_id} not found")
        self.fact_id = fact_id


class FactVotingEngine(Protocol):
    """Minimal engine contract required by the fact voting workflow."""

    async def get_fact(self, fact_id: int, tenant_id: str) -> Fact | dict[str, Any] | None: ...

    async def vote_v2(self, fact_id: int, agent_id: str, value: int) -> float: ...


def _get_confidence(fact: Fact | dict[str, Any] | None) -> str:
    """Read confidence from either the dataclass or the legacy dict surface."""

    if fact is None:
        return "unknown"
    if isinstance(fact, dict):
        return str(fact.get("confidence", "unknown"))
    return fact.confidence


async def record_fact_vote(
    *,
    engine: FactVotingEngine,
    fact_id: int,
    tenant_id: str,
    agent_id: str,
    vote: int,
) -> VoteResponse:
    """Execute the fact voting workflow independently of the HTTP transport."""

    fact = await engine.get_fact(fact_id, tenant_id=tenant_id)
    if not fact:
        raise FactVoteNotFoundError(fact_id)

    score = await engine.vote_v2(fact_id, agent_id, vote)
    updated_fact = await engine.get_fact(fact_id, tenant_id=tenant_id)

    return VoteResponse(
        fact_id=fact_id,
        agent=agent_id,
        vote=vote,
        new_consensus_score=score,
        confidence=_get_confidence(updated_fact),
    )
