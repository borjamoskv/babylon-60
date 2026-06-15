import asyncio
import glob
import time
from pathlib import Path

from cortex.engine.swarm_10k import SwarmCommander


async def run_dispatch():
    bus_path = Path("./cortex_swarm_1000_bus")
    commander = SwarmCommander(bus_path=bus_path)
    await commander.initialize()

    # Gather files for forensic audit
    target_files = glob.glob("**/*.py", recursive=True)
    if not target_files:
        print("No target files found.")
        return

    # Generate 1000 tasks (distributing files among them)
    tasks = []
    for i in range(1000):
        target = target_files[i % len(target_files)]
        tasks.append(
            {"domain": "forensic", "id": i, "task_type": "antipattern_audit", "target": target}
        )

    print(f"🔱 Deploying Forensic Swarm: LEGION-1000 ({len(target_files)} files target)")
    t0 = time.perf_counter()
    async with commander.strike_mode("forensic"):
        await commander.execute_global_dispatch(tasks)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    report = await commander.get_density_report()

    print("\n[FORENSIC DISPATCH TELEMETRY]")
    print(f"Total Agents Deployed: {report['agents']}")
    print(f"Centurions Spawned: {report['centurions']}")
    print(f"Legions Forged: {report['legions']}")
    print(f"Wall-Clock Time: {elapsed_ms:.2f} ms")
    print(f"Audit Throughput: {report['agents'] / (elapsed_ms / 1000):.2f} nodes/sec")

    await commander.consolidate_and_annihilate()
    print(
        "\nAnti-pattern mapping consolidated and annihilated successfully. Zero entropy remaining."
    )


if __name__ == "__main__":
    asyncio.run(run_dispatch())
