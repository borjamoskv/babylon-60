import asyncio
from pathlib import Path

from cortex.engine.swarm_10k import SwarmCommander


async def run():
    commander = SwarmCommander(bus_path=Path("/tmp/cortex_10k_stress"))
    await commander.initialize()
    tasks = [
        {"id": i, "domain": f"domain_{i % 10}", "payload": "stress_test"} for i in range(10000)
    ]
    await commander.execute_global_dispatch(tasks, parallel=True)
    await commander.consolidate_and_annihilate()


asyncio.run(run())
