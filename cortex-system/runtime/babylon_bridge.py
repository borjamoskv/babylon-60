"""
C5-REAL: BABYLON-60 Bridge Adapter for Reality Loop
Author: Borja Moskv / borjamoskv
"""

from typing import Dict, Any
import logging
import asyncio

from babylon60.engine.causal.artist_cortex import (
    OptimizationVector,
    ArtistTelemetryFact,
    ApoptosisEngine,
)

logger = logging.getLogger("cortex.system.babylon_bridge")

MUTATION_BOUNDS = {
    "originality_threshold": {
        "min": 0.20,
        "max": 0.95,
        "step": 0.01,
        "owner": "CriticB",
    },
    "attention_yield_threshold": {
        "min": 0.35,
        "max": 0.95,
        "step": 0.01,
        "owner": "DistributorD",
    },
    "execution_friction_ms": {
        "min": 0,
        "max": 180000,
        "step": 1000,
        "owner": "AssemblerC",
    },
    "distribution_threshold": {
        "min": 0.20,
        "max": 0.95,
        "step": 0.01,
        "owner": "DistributorD",
    },
}

class ArtistCortexEventAdapter:
    def __init__(self):
        self.vector = OptimizationVector()
        self.mutation_accepted = False

    def _validate_bounds(self, parameter: str, value: float) -> bool:
        if parameter not in MUTATION_BOUNDS:
            return False
        bounds = MUTATION_BOUNDS[parameter]
        if not (bounds["min"] <= value <= bounds["max"]):
            return False
        return True

    async def on_mutation_requested(self, event: Any) -> None:
        # Compatibility with both cortex Event and babylon payload dicts
        payload = getattr(event, "payload", event) if not isinstance(event, dict) else event
        
        logger.info(f"[Bridge] Mutation requested: {payload}")
        param = payload.get("parameter")
        new_val = payload.get("new_value")
        
        if not self._validate_bounds(param, new_val):
            logger.warning(f"[Bridge] Mutation rejected: {param}={new_val} out of bounds")
            self.mutation_accepted = False
            return
            
        # Mutate runtime instance first
        if hasattr(self.vector, param):
            setattr(self.vector, param, new_val)
            logger.info(f"[Bridge] Runtime OptimizationVector mutated: {param}={new_val}")
            self.mutation_accepted = True

    async def on_telemetry_observed(self, event: Any) -> None:
        payload = getattr(event, "payload", event) if not isinstance(event, dict) else event
        logger.info(f"[Bridge] Telemetry observed: {payload}")
        
    async def on_apoptosis_lock_requested(self, event: Any) -> None:
        payload = getattr(event, "payload", event) if not isinstance(event, dict) else event
        logger.info(f"[Bridge] Apoptosis lock requested: {payload}")
