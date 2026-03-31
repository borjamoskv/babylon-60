"""
Strike Actuator - Route execution of financial vectors.
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    pass

logger = logging.getLogger("ouroboros.strike")


class StrikeVector(Enum):
    VECTOR_A_BOUNTY = "algora_bounty"
    VECTOR_L_SAAS = "b2b_saas"


class StrikeActuator:
    def __init__(self, use_dry_run: bool = True):
        self.use_dry_run = use_dry_run

        # Load sovereign vault credentials
        vault_path = Path(__file__).resolve().parent.parent.parent.parent / ".env.cortex-sovereign"
        if vault_path.exists():
            try:
                load_dotenv(vault_path)
            except NameError:
                pass  # Fallback if dotenv not installed

        self.devin_key = os.environ.get("DEVIN_API_KEY", "")
        self.mercor_key = os.environ.get("MERCOR_API_KEY", "")
        self.github_token = os.environ.get("GITHUB_TOKEN", "")

    async def strike(self, vector: StrikeVector, target_payload: dict, swarm_manager: Any) -> dict:
        target_id = target_payload.get("id", "UNKNOWN")
        logger.info(
            "[STRIKE ACTUATOR] Launching vector %s against target %s", vector.value, target_id
        )

        if self.use_dry_run:
            logger.info("[DRY RUN] Would execute Native Swarm payload for %s", target_id)
            return {
                "status": "cleared_dry_run",
                "net_yield": target_payload.get("expected_yield", 0.0),
                "compute_cost": target_payload.get("compute_cost", 0.0),
                "strike_vector": vector.value,
            }

        # Actual autonomous process execution via CORTEX OMEGA Swarm
        logger.warning("[LIVE] Dispatching Native CORTEX OMEGA Swarm for %s!", vector.value)

        if vector == StrikeVector.VECTOR_A_BOUNTY:
            try:
                target_url = target_payload.get("url")
                prompt = (
                    f"Resolve priority task targeting {target_url} using available context. "
                    "Adhere to CORTEX P0 constraints."
                )

                # AX-1000 Sovereign Integration
                responses = await swarm_manager.deploy_squad(
                    task=prompt, count=100, squad_type="OMEGA"
                )

                if responses and len(responses) > 0:
                    primary_response = responses[0]
                    metadata = primary_response.get("metadata", {})
                    return {
                        "status": primary_response.get("status", "success"),
                        "net_yield": target_payload.get("expected_yield", 0.0),
                        "compute_cost": target_payload.get("compute_cost", 0.0),
                        "strike_vector": vector.value,
                        "session_id": "native_omega_swarm",
                        "exergy": metadata.get("exergy", 0.0),
                        "cycles": metadata.get("cycles", 1),
                        "error": primary_response.get("error"),
                    }
                else:
                    return {
                        "status": "failed",
                        "net_yield": 0.0,
                        "compute_cost": 0.0,
                        "strike_vector": vector.value,
                        "error": "Omega Swarm returned no responses",
                    }

            except Exception as e:
                logger.error("Failed to dispatch OMEGA payload for %s: %s", target_id, e)
                return {
                    "status": "failed",
                    "net_yield": 0.0,
                    "compute_cost": 0.0,
                    "strike_vector": vector.value,
                    "error": str(e),
                }

        return {
            "status": "deployed_unsupported_vector",
            "net_yield": 0.0,
            "compute_cost": 0.0,
            "strike_vector": vector.value,
        }
