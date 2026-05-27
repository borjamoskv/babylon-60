import asyncio
import time
import logging
from persistence import HybridPersistenceManager, enqueue_swarm_task, get_swarm_metrics

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("c5_demo")

async def main():
    logger.info("Initializing C5-REAL Sovereign Substrate...")
    # Initialize the persistence manager which starts the OutboxDaemon and other guardians
    manager = HybridPersistenceManager()
    
    logger.info("Current System Health: %s", manager.get_system_health())
    
    logger.info("Enqueuing 100 high-exergy swarm tasks...")
    for i in range(100):
        # Dispatch tasks at C5-REAL speed
        enqueue_swarm_task(f"agent_sigma_{i}", {"command": "EXECUTE_AST_MUTATION", "entropy": i * 0.1})
        
    logger.info("Tasks enqueued. Awaiting OutboxDaemon Zero-Latency Drain...")
    
    # Wait for the OutboxDaemon to process the tasks asynchronously
    # The outbox_wake_event should trigger it immediately
    for _ in range(10):
        metrics = manager.get_system_health()
        swarm_metrics = get_swarm_metrics(bypass_cache=True)
        logger.info("Health: %s | Swarm: %s", metrics, swarm_metrics)
        
        # If tasks were processed from the Ring Buffer, they don't immediately reflect 
        # in the SQLite pending count, but the logger inside drain_once_sync will show it
        await asyncio.sleep(0.5)

    logger.info("Final System Health: %s", manager.get_system_health())
    logger.info("Demonstration C5-REAL Complete.")

if __name__ == "__main__":
    asyncio.run(main())
