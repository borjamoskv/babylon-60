from __future__ import annotations

from typing import Any


class LegacyMixin:
    """Compatibility aliases that still add unique public surface.

    CRUD and query wrappers now live directly on ``CortexEngine``. Keeping those
    same wrappers here only widens the legacy MRO surface with dead duplicates.
    """

    async def get_votes(self, fact_id: int, tenant_id: str = "default") -> list[dict[str, Any]]:
        return await self.consensus.get_votes(fact_id, tenant_id=tenant_id)

    async def verify_vote_ledger(self, tenant_id: str = "default") -> dict[str, Any]:
        return await self.consensus.verify_vote_ledger(tenant_id=tenant_id)

    async def slash_vote_deviation(
        self,
        agent_id: str,
        fact_id: int,
        penalty_type: float,
        reason: str,
        tenant_id: str = "default",
    ) -> float:
        return await self.consensus.slash_vote_deviation(
            agent_id=agent_id,
            fact_id=fact_id,
            penalty_type=penalty_type,
            reason=reason,
            tenant_id=tenant_id,
        )
