import asyncio
from cortex.engine.swarm_10k import SwarmCommander

async def main():
    commander = SwarmCommander(bus_path="/tmp")
    await commander.initialize()
    await commander.execute_global_dispatch([{"domain": "test", "id": i} for i in range(10)])
    print(commander.legions["test"].centurions)
    await commander.consolidate_and_annihilate()

if __name__ == "__main__":
    asyncio.run(main())
