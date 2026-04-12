"""CORTEX v6.3 — RLVR (Reinforcement Learning from Verifiable Rewards) Evaluator.

This module evaluates the thermodynamic cost and objective success of operations,
assigning a continuous Q-value (reward/penalty) to actions to evolve the Swarm's
procedural memory.
"""

import logging

logger = logging.getLogger(__name__)


class RLVREvaluator:
    """
    Evaluates actions thermodynamically.
    Instead of binary pass/fail, it assigns a Q-value [-1.0 to 1.0].
    """

    def __init__(self, target_latency_ms: float = 500.0):
        self.target_latency_ms = target_latency_ms

    def evaluate(self, exit_code: int, latency_ms: float, payload_size: int = 0) -> float:
        """
        Calculates the thermodynamic Q-value reward.
        - Exit code != 0: Massive penalty (-1.0)
        - Exit code == 0: Base reward + 0.5
        - Latency scaling: Bonus if faster than target, penalty if slower
        """
        if exit_code != 0:
            return -1.0

        reward = 0.5

        # Latency optimization (faster = higher reward)
        latency_ratio = self.target_latency_ms / max(latency_ms, 1.0)
        if latency_ratio > 1.0:
            # Faster than target
            reward += min(0.4, (latency_ratio - 1.0) * 0.1)
        else:
            # Slower than target
            reward -= min(0.4, (1.0 - latency_ratio) * 0.2)

        # Hard bounds
        return max(-1.0, min(1.0, reward))
