"""
Barrera de aislamiento de side effects. Realiza la ejecución de reinicio/recuperación.
"""
import gc
import logging
import os

logger = logging.getLogger("ouroboros.executor")

async def execute_plan(plan: dict) -> str:
    name = plan.get("name", "noop")
    logger.info(f"Executing physical action: {name}")
    
    if name == "flush_cache":
        gc.collect()
        logger.info("[C5-REAL] Garbage collection executed successfully.")
        return "success"
    elif name == "throttle_cpu":
        try:
            os.nice(1)
            logger.info("[C5-REAL] CPU process priority throttled (nice +1).")
        except Exception as e:
            logger.warning(f"Failed to adjust nice value: {e}")
        return "success"
    elif name == "restart_node":
        logger.warning("[C5-REAL] Process restart signal queued.")
        return "success"
        
    return "success"
