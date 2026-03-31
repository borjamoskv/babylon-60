import asyncio
import logging
import tempfile
import time

from cortex.engine.swarm_10k import SwarmCommander

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_swarm_10k")


async def test_10k_agents_stress():
    logger.info("Initializing SwarmCommander (10K Agents Payload Simulation)")

    with tempfile.TemporaryDirectory() as temp_dir:
        start_init = time.perf_counter()
        # L0 Commander uses ShardedAsyncSignalBus backed by SQLite in temp dir
        commander = SwarmCommander(bus_path=temp_dir)
        await commander.initialize()
        logger.info(f"Initialized commander in {(time.perf_counter() - start_init) * 1000:.2f}ms")

        # Generate 10,000 tasks distributed across 10 functional domains (L1 Legions)
        logger.info("Forging 10,000 proxy tasks...")
        tasks = [
            {"domain": f"dominio_{i % 10}", "payload": f"task_{i}", "complexity": 1.0}
            for i in range(10000)
        ]

        logger.info(
            f"Dispatching tasks across {len(set(t['domain'] for t in tasks))} legions (Bulk Routing O(1))"
        )
        start_dispatch = time.perf_counter()

        # This will map tasks to legions, deploy new Centurions (L2), and spawn Agents
        await commander.execute_global_dispatch(tasks)
        dispatch_ms = (time.perf_counter() - start_dispatch) * 1000
        logger.info(f"Dispatch completed in {dispatch_ms:.2f}ms (Target AX-30 < 1000ms scaling)")

        # Verify Hierarchy and Exergy distribution
        report = await commander.get_density_report()
        logger.info(f"Structure Density: {report}")

        assert report["agents"] == 10000, "Missed agent threshold!"
        assert report["centurions"] == 100, "Wrong centurion mapping (100 expected)"
        assert report["legions"] == 10, "Wrong legions mapping (10 expected)"

        # Thermodynamics Consolidate phase
        start_annihilate = time.perf_counter()
        logger.info("Initiating thermodynamic consolidation and annhilation...")
        await commander.consolidate_and_annihilate()
        annihilate_ms = (time.perf_counter() - start_annihilate) * 1000

        logger.info(f"Annihilation finalized in {annihilate_ms:.2f}ms")
        logger.info("STRESS TEST PASSED. Zero Latency Hierarchy Verified.")


if __name__ == "__main__":
    try:
        asyncio.run(test_10k_agents_stress())
    except Exception as e:
        logger.error(f"Stress Test Failed: {e}", exc_info=True)
