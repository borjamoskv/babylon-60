# [C5-REAL] Exergy-Maximized
import asyncio
import logging

from cortex.swarm.autopulse import process_queue

logger = logging.getLogger("cortex.swarm")

def start_swarm_daemon():
    """Start the Swarm Autopoiesis engine as an asyncio background task."""
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(process_queue())
        logger.info("[Swarm] Autopulse background task spawned successfully.")
        return task
    except RuntimeError:
        logger.error("[Swarm] Failed to start daemon: No running event loop found.")
        return None
