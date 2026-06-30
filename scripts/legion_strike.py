# [C5-REAL] Exergy-Maximized
"""
cat_id: legion-strike
cat_type: script
version: 1.1.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P1
"""

import argparse
import asyncio
import logging
import sys

from babylon60.core import config
from babylon60.extensions.llm.router import CortexLLMRouter
from babylon60.extensions.swarm.centauro_engine import CentauroEngine

logger = logging.getLogger("cortex.legion_strike")

async def main():
    parser = argparse.ArgumentParser(
        description="LEGIØN-1 Sovereign Swarm Protocol Strike Interface"
    )
    parser.add_argument("--mission", required=True, help="Mission objective for the Swarm")
    parser.add_argument(
        "--formation",
        default="BLITZ",
        choices=[
            "BLITZ",
            "PHALANX",
            "SIEGE",
            "HYDRA",
            "ORACLE",
            "PHOENIX",
            "CHIMERA",
            "LEVIATHAN",
            "OUROBOROS",
            "SENTINEL",
            "SPECTRE",
            "GHOST",
            "TESTUDO",
            "SANEDRIN",
            "CENTURIA",
        ],
        help="Tactical formation to deploy",
    )
    parser.add_argument(
        "--tolerance", type=float, default=0.67, help="Byzantine consensus tolerance"
    )
    parser.add_argument("--sim", action="store_true", help="Force C4-SIM mode (No LLM calls)")
    parser.add_argument("--provider", help="Primary LLM provider (default: read from config)")
    parser.add_argument("--model", help="Primary LLM model (default: read from config)")

    args = parser.parse_args()

    # Dynamic LLM Provider configuration from config singleton or CLI overrides
    primary_provider_name = args.provider or config.LLM_PROVIDER or "gemini"
    primary_model_name = args.model or config.LLM_MODEL or "gemini-2.5-flash"

    # Despertar del Router (C5-REAL awakening)
    if not args.sim:
        from babylon60.extensions.llm.provider import LLMProvider

        primary_provider = LLMProvider(provider=primary_provider_name, model=primary_model_name)
        fallback_providers = [
            LLMProvider("openrouter"),
            LLMProvider("deepseek"),
            LLMProvider("ollama"),
            LLMProvider("lmstudio"),
        ]
        router = CortexLLMRouter(primary=primary_provider, fallbacks=fallback_providers)
    else:
        router = None

    engine = CentauroEngine(tolerance=args.tolerance, router=router)

    print("🔱 LEGIØN-1 ACTIVATED")
    print(f"MISSION: {args.mission}")
    print(f"FORMATION: {args.formation}")
    print(f"PRIMARY PROVIDER: {primary_provider_name}")
    print(f"PRIMARY MODEL: {primary_model_name}")
    print(f"MODE: {'C4-SIM' if args.sim else 'C5-REAL'}")
    print("Executing Byzantine Consensus Quorum...")

    try:
        result = await engine.engage(mission=args.mission, formation=args.formation)

        status_val = result.get("status")
        agents_used = result.get("agents_used")
        formation_val = result.get("formation")
        solution_val = result.get("solution")

        print("\n[RESULT]")
        print(f"STATUS: {status_val}")
        print(f"AGENTS USED: {agents_used}")
        print(f"FINAL FORMATION: {formation_val}")
        if "reason" in result:
            reason_val = result.get("reason")
            print(f"REASON: {reason_val}")

        print("\n[BYZANTINE REPUTATION BOARD]")
        for agent_id, agent in engine.agents.items():
            node = engine.consensus.nodes.get(agent_id)
            rep = node.reputation if node else 1.0
            stars = "★" * int(round(rep * 5))
            warning = " [SLASHED]" if rep < 0.9 else ""
            print(f"⬡ {agent_id} ({agent.specialty}): {rep:.2f} {stars}{warning}")

        print("\n[SOLUTION]")
        print(solution_val)

        if status_val == "success" or status_val == "aleph_breakthrough":
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
