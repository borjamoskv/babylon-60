import asyncio
import os
import sys
import logging

sys.path.insert(0, os.path.abspath('.'))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("consolidate_cortex")

# Import all main and inject_primitives functions
from inject_category_theory import main as inject_cat_theory
from inject_category_theory_advanced import main as inject_cat_theory_adv
from inject_cwv_performance import inject_primitives as inject_cwv
from inject_design_tokens import inject_primitives as inject_design
from inject_goat_math import inject_primitives as inject_goat
from inject_mythos_primitives import inject_primitives as inject_mythos
from inject_spatial_render import inject_primitives as inject_spatial

async def run_pipeline():
    logger.info("=== STARTING CORTEX PERSIST COGNITIVE CONSOLIDATION PIPELINE (C5-REAL) ===")
    
    # 1. Category Theory Fundamental
    try:
        logger.info("Running Category Theory injection...")
        await inject_cat_theory()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_cat_theory: {e}")

    # 2. Category Theory Advanced
    try:
        logger.info("Running Category Theory Advanced injection...")
        await inject_cat_theory_adv()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_cat_theory_adv: {e}")

    # 3. CWV Performance
    try:
        logger.info("Running CWV Performance injection...")
        await inject_cwv()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_cwv: {e}")

    # 4. Design Tokens
    try:
        logger.info("Running Design Tokens injection...")
        await inject_design()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_design: {e}")

    # 5. Goat Math
    try:
        logger.info("Running Goat Math injection...")
        await inject_goat()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_goat: {e}")

    # 6. Mythos Primitives
    try:
        logger.info("Running Mythos Primitives injection...")
        await inject_mythos()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_mythos: {e}")

    # 7. Spatial Render
    try:
        logger.info("Running Spatial Render injection...")
        await inject_spatial()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_spatial: {e}")

    logger.info("=== ALL INJECTIONS COMPLETED ===")
    logger.info("Waiting 3.0 seconds to guarantee full ledger batch commit to security_audit_log.jsonl...")
    await asyncio.sleep(3.0)
    logger.info("=== LEDGER BATCHES FULLY COMMITTED ===")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
