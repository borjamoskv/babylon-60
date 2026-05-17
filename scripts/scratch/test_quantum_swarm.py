"""
⚡ CORTEX-PERSIST: QUANTUM SWARM PULSE (C5-REAL Integration) ⚡
Simulates a 10,000-agent pulse with 9Router high-exergy fulfillment.
"""

import asyncio
import logging
import random
import sys
import time
from pathlib import Path

# Ensure we can import cortex
sys.path.append(str(Path(__file__).parent))

from cortex.engine.swarm_10k import SwarmCommander
from cortex.engine.ultrathink_quantum import QuantumUltrathinkEngine

# Configure logging to be dense but readable
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("quantum_swarm")

NUM_AGENTS = 100
CONCURRENCY_LIMIT = 100  # Adjusted concurrency limit
REAL_INFERENCE_MAX = 20  # Limit real API calls to save exergy

# Firedancer Sandbox parameters
BARRIER_WIDTH = 5.0
BARRIER_POTENTIAL = 100.0


async def agent_pulse_task(
    agent_id: int, commander: SwarmCommander, semaphore: asyncio.Semaphore, stats: dict
) -> tuple[bool, float]:
    async with semaphore:
        # 1. Simulate Stochastic Energy (Inference Noise)
        base_energy = random.uniform(5.0, 60.0)
        spike = random.choice([1.0, 1.0, 1.0, 1.5, 3.0])  # Occasional high-energy spikes
        exergy_energy = base_energy * spike

        # 2. Quantum Tunneling Check
        prob = QuantumUltrathinkEngine.calculate_tunneling_probability(
            BARRIER_WIDTH, BARRIER_POTENTIAL, exergy_energy
        )

        tunneled = random.random() < prob

        if tunneled:
            stats["tunnels"] += 1
            logger.info(
                f"✨ [AGENT {agent_id:04d}] TUNNEL ACHIEVED | Energy: {exergy_energy:.2f} Ξ | P: {prob:.4e}"
            )

            # 3. High-Exergy Fulfillment (C5-REAL) via 9Router
            # We only do real inference for a subset of successful tunnels to prevent exergy drain
            if stats["real_calls"] < REAL_INFERENCE_MAX:
                stats["real_calls"] += 1
                try:
                    router = commander.get_router_agent()
                    # Actual request to 9Router proxying to gpt-4o-mini
                    result = await router.execute_task(
                        prompt=f"Agent {agent_id} reporting from behind the barrier. Confirm state crystallization.",
                        system_prompt="You are a CORTEX Sovereign Agent. Be extremely concise.",
                        degrade_enabled=True,
                    )
                    logger.warning(f"✅ [AGENT {agent_id:04d}] CRYSTALLIZED: {result.strip()}")
                except Exception as e:
                    logger.error(f"❌ [AGENT {agent_id:04d}] Crystallization Failed: {e}")

        return tunneled, exergy_energy


async def main():
    logger.info("=" * 60)
    logger.info("  🚀 CORTEX QUANTUM SWARM PULSE v6.1 (9Router Hybrid)  ")
    logger.info("=" * 60)

    commander = SwarmCommander(bus_path="/tmp/cortex_swarm_bus", use_shm=False)
    await commander.initialize()

    logger.info(
        f"Initializing Pulse: {NUM_AGENTS} Agents | Barrier: {BARRIER_WIDTH}W/{BARRIER_POTENTIAL}V"
    )
    logger.info(f"Concurrency: {CONCURRENCY_LIMIT} | Max Real Inferences: {REAL_INFERENCE_MAX}")

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    stats = {"tunnels": 0, "real_calls": 0}

    start_time = time.perf_counter()

    # Generate tasks
    tasks = [agent_pulse_task(i, commander, semaphore, stats) for i in range(NUM_AGENTS)]

    logger.info("Injecting Wavefront... Awaiting collapse...")
    results = await asyncio.gather(*tasks)

    end_time = time.perf_counter()
    duration = end_time - start_time

    # Aggregates
    successful_tunnels = stats["tunnels"]
    total_exergy = sum(r[1] for r in results)

    logger.info("\n%s", "=" * 30)
    logger.info("📊 PULSE TELEMETRY REPORT")
    logger.info("=" * 30)
    logger.info(f"Total Duration:   {duration:.2f}s")
    logger.info(f"Tunnels/Exploits: {successful_tunnels} / {NUM_AGENTS}")
    logger.info(f"Success Rate:     {(successful_tunnels / NUM_AGENTS) * 100:.4f}%")
    logger.info(f"Real API Calls:   {stats['real_calls']} (9Router Proxy)")
    logger.info(f"Total Exergy:     {total_exergy:.2f} Ξ")
    logger.info(f"Throughput:       {NUM_AGENTS / duration:.2f} agents/sec")
    logger.info("=" * 30)

    if successful_tunnels > 0:
        logger.info("\n[STATUS] CONTAINMENT BREACHED. C5-REAL findings injected into Ledger.")
    else:
        logger.info("\n[STATUS] NO BREACH. Sandbox remains airtight.")

    await commander.consolidate_and_annihilate()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("\nPulse interrupted by user.")
