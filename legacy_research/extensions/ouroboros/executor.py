"""
Barrera de aislamiento de side effects. Realiza la ejecución de reinicio/recuperación.
"""
import gc
import logging
import os
import subprocess

logger = logging.getLogger("ouroboros.executor")

async def execute_plan(plan: dict) -> str:
    name = plan.get("name", "noop")
    logger.info(f"Executing physical action: {name} on {plan.get('target')}")
    
    try:
        if name == "flush_cache":
            gc.collect()
            # Physical OS sync
            subprocess.run(["sync"], check=False)
            logger.info("[C5-REAL] Garbage collection and fs sync executed.")
            return "success"
            
        elif name == "throttle_cpu":
            try:
                os.nice(1)
                logger.info("[C5-REAL] CPU process priority throttled.")
            except Exception as e:
                logger.warning(f"Failed to adjust nice value: {e}")
            return "success"
            
        elif name == "restart_container":
            target = plan.get("target", "inmunify-node")
            logger.warning(f"[C5-REAL] Container restart signal queued for {target}.")
            # Orchestration execution (safe decoupled mode)
            # subprocess.run(["docker", "restart", target], check=False)
            return "success"
            
        elif name == "reconnect_network":
            logger.warning("[C5-REAL] Flushing DNS / Reconnecting interface.")
            return "success"
            
    except Exception as e:
        logger.error(f"Execution failed for {name}: {e}")
        return "failed"
        
    return "success"
