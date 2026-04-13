#!/usr/bin/env python3
"""CORTEX Quickstart: Multi-Agent Byzantine Consensus.

Demonstrates how CORTEX verifies decisions across multiple agents
using Weighted Byzantine Fault-Tolerant (WBFT) consensus.

Usage:
    python examples/quickstart/multi_agent_consensus.py
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path


async def main() -> None:
    db_path = Path(tempfile.mkdtemp()) / "consensus.db"

    from cortex import CortexEngine

    engine = CortexEngine(db_path=str(db_path), auto_embed=False)
    await engine.init_db()

    print("🤝 CORTEX Quickstart — Multi-Agent Consensus\n")

    # --- Step 1: Store the fact under review ---
    print("1️⃣  Storing the decision under review...\n")
    fact_id = await engine.store(
        content="Market conditions favor conservative allocation",
        fact_type="decision",
        project="consensus-demo",
        source="swarm:proposer",
    )
    print(f"   📝 Fact #{fact_id} stored")

    # --- Step 2: Register agents and cast votes ---
    print("\n2️⃣  Registering agents and casting votes...")
    a1 = await engine.consensus.register_agent("analyst-1")
    a2 = await engine.consensus.register_agent("analyst-2")
    a3 = await engine.consensus.register_agent("analyst-3")

    score_1 = await engine.consensus.vote_v2(fact_id, a1, 1, reason="Risk posture is conservative")
    score_2 = await engine.consensus.vote_v2(fact_id, a2, 1, reason="Matches treasury policy")
    score_3 = await engine.consensus.vote_v2(fact_id, a3, -1, reason="Growth mandate disagreement")

    print(f"   analyst-1 -> verify   | score now {score_1:.3f}")
    print(f"   analyst-2 -> verify   | score now {score_2:.3f}")
    print(f"   analyst-3 -> dispute  | score now {score_3:.3f}")

    # --- Step 3: Inspect the resulting consensus state ---
    print("\n3️⃣  Inspecting consensus state...")
    fact = await engine.get_fact(fact_id)
    votes = await engine.get_votes(fact_id)
    vote_ledger = await engine.verify_vote_ledger()
    print(f"   Votes recorded: {len(votes)}")
    print(f"   Consensus score: {fact.consensus_score if fact else 'unknown'}")
    print(f"   Confidence: {fact.confidence if fact else 'unknown'}")
    print(f"   Vote ledger valid: {vote_ledger.get('valid', False)}")

    print("\n✨ Multi-agent consensus demonstration complete.")
    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
