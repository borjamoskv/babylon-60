# [C5-REAL] Exergy-Maximized
"""
Sovereign Swarm 10,000-Agent Project Consolidation.
Delegates to the C5-REAL Deterministic Consolidation Workflow governed by MTK.
"""

import asyncio
from cortex.engine.consolidation_workflow import run_deterministic_consolidation

async def run_consolidation():
    # Pass a valid test key or load from env in a real scenario
    await run_deterministic_consolidation("test_private_key_C5_REAL")

if __name__ == "__main__":
    asyncio.run(run_consolidation())
