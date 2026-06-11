# [C5-REAL] Exergy-Maximized
"""Predefined species templates for agent generation."""

from __future__ import annotations

from cortex.engine.genome import StrategyGenome
from cortex.isa.builder import (
    Predicate,
    bind,
    cond,
    dispatch,
    halt,
    par,
    seq,
)


class AgentSpecies:
    """Predefined species templates for agent generation.

    Each species defines a structural archetype that Genesis can
    instantiate, parameterize, and evolve. These are the "seed"
    genomes that evolution operates on.
    """

    @staticmethod
    def hunter(domain: str = "general", targets: int = 3) -> StrategyGenome:
        """Fan-out hunter: parallel scan → aggregate → report."""
        hunters = [
            dispatch(
                f"hunter_{domain}_{i}",
                {"mode": "scan", "domain": domain},
                id=100 + i,
            )
            for i in range(targets)
        ]
        tree = seq(
            bind("domain", domain),
            par(*hunters),
            dispatch("aggregator", {"collect": True, "domain": domain}, id=200),
            dispatch("reporter", {"emit": True}, id=300),
        )
        return StrategyGenome(
            name=f"hunter_{domain}",
            dispatch_tree=tree,
            parameters={
                "scan_depth": 3,
                "timeout_ms": 5000,
                "min_confidence": 0.7,
            },
            constraints=["must_have_aggregator", "min_hunters_2"],
        )

    @staticmethod
    def pipeline(stages: list[str] | None = None) -> StrategyGenome:
        """Sequential pipeline: ingest → process → validate → emit."""
        stages = stages or ["ingest", "process", "validate", "emit"]
        tree = seq(
            *[
                dispatch(
                    f"pipeline_{stage}",
                    {"phase": i + 1, "stage": stage},
                    id=100 + i,
                )
                for i, stage in enumerate(stages)
            ]
        )
        return StrategyGenome(
            name="pipeline",
            dispatch_tree=tree,
            parameters={
                "batch_size": 100,
                "retry_count": 2,
                "checkpoint_interval": 50,
            },
            constraints=["sequential_order_preserved"],
        )

    @staticmethod
    def guardian(domain: str = "security") -> StrategyGenome:
        """Conditional guardian: scan → decide → act or alert."""
        tree = seq(
            dispatch("guardian_scan", {"domain": domain}, id=100),
            cond(
                Predicate.always(),
                then_branch=seq(
                    dispatch("guardian_act", {"mode": "enforce"}, id=201),
                    dispatch("guardian_log", {"mode": "audit"}, id=202),
                ),
                else_branch=dispatch("guardian_alert", {"severity": "high"}, id=300),
            ),
        )
        return StrategyGenome(
            name=f"guardian_{domain}",
            dispatch_tree=tree,
            parameters={
                "threat_threshold": 0.8,
                "alert_cooldown_ms": 10000,
                "max_enforcement_level": 3,
            },
            constraints=["must_log_actions", "alert_on_failure"],
        )

    @staticmethod
    def explorer(depth: int = 3) -> StrategyGenome:
        """Recursive explorer: scout → evaluate → branch → recurse."""
        inner = dispatch("explorer_evaluate", {"depth": depth}, id=100)
        for d in range(depth):
            inner = seq(
                dispatch(f"explorer_scout_{d}", {"level": d}, id=200 + d),
                cond(
                    Predicate.always(),
                    then_branch=inner,
                    else_branch=halt(error=f"dead_end_depth_{d}"),
                ),
            )
        return StrategyGenome(
            name="explorer",
            dispatch_tree=inner,
            parameters={
                "max_depth": depth,
                "branch_factor": 2,
                "curiosity_weight": 0.6,
            },
        )

    @staticmethod
    def swarm_coordinator(swarm_size: int = 5) -> StrategyGenome:
        """Swarm coordinator: init → fan-out workers → collect → synthesize."""
        workers = [
            dispatch(
                f"swarm_worker_{i}",
                {"worker_id": i},
                id=100 + i,
            )
            for i in range(swarm_size)
        ]
        tree = seq(
            dispatch("swarm_init", {"size": swarm_size}, id=50),
            par(*workers),
            dispatch("swarm_collect", {"expected": swarm_size}, id=200),
            dispatch("swarm_synthesize", {}, id=300),
        )
        return StrategyGenome(
            name="swarm_coordinator",
            dispatch_tree=tree,
            parameters={
                "swarm_size": swarm_size,
                "consensus_threshold": 0.67,
                "timeout_per_worker_ms": 3000,
            },
            constraints=["quorum_required"],
        )
