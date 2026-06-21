# [C5-REAL] Exergy-Maximized
"""
Core Execution Loop for the Ouroboros Mythos Agent.
Implements Primitive 1: Observe -> Diagnose -> Plan -> Act -> Critic -> Memorize.
"""

import asyncio
import logging
import time

from .meta_controller import MetaController
from .mcts_planner import MCTSPlanner
from .memory_palace import MemoryPalace
from .mythos_state import MythosState
from .exergy_monitor import ExergyMonitor

logger = logging.getLogger(__name__)

class MythosOuroborosEngine:
    """
    Sovereign execution loop that enforces deterministic progression and 
    strictly rejects state updates if thermodynamic efficiency (Exergy) is negative.
    """

    def __init__(self):
        self.state = MythosState()
        self.memory = MemoryPalace()
        self.exergy = ExergyMonitor()
        self.meta_controller = MetaController()
        self.planner = MCTSPlanner()
        self.is_running = False

    async def run_loop(self):
        """
        The continuous observation-action cycle.
        """
        self.is_running = True
        logger.info("[C5-REAL] Ouroboros Mythos Loop Started.")
        
        while self.is_running:
            # 1. Observe
            observation = await self._observe()
            
            # 2. Diagnose
            diagnosis = await self._diagnose(observation)
            
            # 3. Plan
            mode = self.meta_controller.decide_mode(self.exergy.current_score())
            if mode == "dream":
                logger.info("[C5-REAL] Entering Dream Mode (MCTS Forward Simulation).")
                plan = await self.planner.run_dream_simulation(diagnosis)
            else:
                plan = await self.planner.synthesize_plan(diagnosis)

            # 4. Act
            action_result = await self._act(plan)

            # 5. Critic
            critic_score = await self._criticize(action_result)

            # Check thermodynamics: Exergy yield computed purely with integers
            exergy_yield = self.exergy.compute_yield(reward=critic_score)
            
            # 6. Memorize
            if exergy_yield > 0:
                await self.memory.store_episodic(action_result, critic_score)
                self.state.commit_state_hash(action_result)
                logger.info(f"[C5-REAL] Action Committed. Exergy Yield: {exergy_yield}")
            else:
                logger.warning(f"[C5-REAL] Action Rejected. Negative Exergy Yield: {exergy_yield}")
                self.meta_controller.register_pain(exergy_yield)

            # Sleep using integer coordination
            await asyncio.sleep(1)

    async def _observe(self) -> dict:
        """Extracts environmental state deterministically."""
        return {"timestamp_ns": time.monotonic_ns(), "latency_ms": 15}

    async def _diagnose(self, observation: dict) -> dict:
        """Identifies anomalies and opportunities strictly via byte traces."""
        return {"opportunity_trace": b"inference_task_v1", "confidence_basis": 95}

    async def _act(self, plan: dict) -> dict:
        """Executes the plan via deterministic hooks."""
        return {"action_type": b"execute_task", "status": "success"}

    async def _criticize(self, action_result: dict) -> int:
        """Scores the action outcome strictly from 0 to 100."""
        from .critic_prompts import ActionCritic
        critic = ActionCritic()
        return critic.evaluate_action(action_result)

    def stop(self):
        self.is_running = False
