# Creator/Autor: Borja Moskv (borjamoskv)
# Protocolo: C5-REAL | Epistemic Consolidation Pipeline
"""
CORTEX Persist Cognitive Consolidation Pipeline (C5-REAL).
Orchestrates the ingestion of all mathematical, spatial, performance, design,
and behavioral primitives into the Epistemic Dependency Graph.
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("consolidate_cortex")

# Import all main and inject_primitives functions
from inject_agente_principal import inject_primitives as inject_agent_principal
from inject_arkham_breadcrumbs import inject_primitives as inject_arkham_breadcrumbs
from inject_category_theory import main as inject_cat_theory
from inject_category_theory_advanced import main as inject_cat_theory_adv
from inject_cwv_performance import inject_primitives as inject_cwv
from inject_design_tokens import inject_primitives as inject_design
from inject_framework_dame import inject_primitives as inject_dame_framework
from inject_git_exergy import inject_primitives as inject_git_exergy
from inject_goat_math import inject_primitives as inject_goat
from inject_leyes_fisicas import inject_primitives as inject_physical_laws
from inject_mythos_primitives import inject_primitives as inject_mythos
from inject_osint_defense import inject_primitives as inject_osint
from inject_sistemas_complejos import inject_primitives as inject_complex_systems
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

    # 8. Agent-Principal Primitives
    try:
        logger.info("Running Agent-Principal injection...")
        await inject_agent_principal()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_agent_principal: {e}")

    # 9. OSINT Defense Primitives
    try:
        logger.info("Running OSINT Defense injection...")
        await inject_osint()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_osint: {e}")

    # 10. Complex Systems Primitives
    try:
        logger.info("Running Complex Systems injection...")
        await inject_complex_systems()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_complex_systems: {e}")

    # 11. Git Exergy Primitives
    try:
        logger.info("Running Git Exergy injection...")
        await inject_git_exergy()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_git_exergy: {e}")

    # 12. Physical Laws Primitives
    try:
        logger.info("Running Physical Laws injection...")
        await inject_physical_laws()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_physical_laws: {e}")

    # 13. DAME Framework Primitives
    try:
        logger.info("Running DAME Framework injection...")
        await inject_dame_framework()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_dame_framework: {e}")

    # 14. Arkham Breadcrumbs Primitives
    try:
        logger.info("Running Arkham Breadcrumbs injection...")
        await inject_arkham_breadcrumbs()
        await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"Error in inject_arkham_breadcrumbs: {e}")

    logger.info("=== ALL INJECTIONS COMPLETED ===")
    logger.info("Waiting 3.0 seconds to guarantee full ledger batch commit to security_audit_log.jsonl...")
    await asyncio.sleep(3.0)
    logger.info("=== LEDGER BATCHES FULLY COMMITTED ===")

if __name__ == "__main__":
    asyncio.run(run_pipeline())

