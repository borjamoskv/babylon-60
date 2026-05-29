"""Tests for SICA Autonomy Primitives and Strategy Persistence.

Validates:
  1. Speculative fork strategy exploration.
  2. Heuristic synthesis from trace patterns.
  3. Meta-meta controller diagnostics and self-corrections.
  4. Adaptive retry budgets.
  5. Proactive autonomous tick execution.
  6. Genome save/load serialization and atomic file I/O.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
import pytest

from cortex.sica.autonomy import (
    AdaptiveRetry,
    AutonomousTick,
    MetaMetaController,
    SpeculativeFork,
    TraceSynthesizer,
)
from cortex.sica.meta_level import FailureClass, MetaAction, MetaJudgment
from cortex.sica.object_level import ExecutionStep, ExecutionTrace, StepOutcome
from cortex.sica.persistence import (
    genome_from_json,
    genome_to_json,
    list_generations,
    load_genome,
    load_or_default,
    save_genome,
)
from cortex.sica.strategy import Heuristic, SearchStrategy, default_genome


# ─── Autonomy Primitives Tests ───────────────────────────────────────


class TestSpeculativeFork:
    def test_speculate_no_mutation_needed(self):
        strategy = SearchStrategy(default_genome())
        forker = SpeculativeFork(n_forks=2)
        judgment = MetaJudgment(
            trace_id="t1",
            failure_class=None,
            is_meta_failure=False,
            confidence=0.5,
            diagnosis="all good",
        )
        res = forker.speculate(strategy, judgment, [])
        assert res is strategy
        assert len(forker.fork_history) == 0

    def test_speculate_forks_and_adopts_best(self):
        strategy = SearchStrategy(default_genome())
        strategy.genome.heuristics[0].weight = 0.5
        
        forker = SpeculativeFork(n_forks=3)
        judgment = MetaJudgment(
            trace_id="t2",
            failure_class=FailureClass.CASCADE_BLINDNESS,
            is_meta_failure=True,
            confidence=0.8,
            diagnosis="cascade detected",
        )
        
        trace = ExecutionTrace(task_id="t2", objective="test", strategy_genome_hash="abc")
        trace.add_step(ExecutionStep(step_id=1, action="test", outcome=StepOutcome.SUCCESS, heuristic_applied=strategy.genome.heuristics[0].name))
        trace.finalize(StepOutcome.SUCCESS)

        res = forker.speculate(strategy, judgment, [trace])
        assert len(forker.fork_history) == 3
        assert res.genome.generation >= strategy.genome.generation


class TestTraceSynthesizer:
    def test_synthesize_under_min_traces(self):
        synth = TraceSynthesizer(min_traces=5)
        heuristics = default_genome().heuristics
        proposals = synth.synthesize([], heuristics)
        assert len(proposals) == 0

    def test_synthesize_tool_combos(self):
        synth = TraceSynthesizer(min_traces=3)
        traces = []
        for i in range(4):
            t = ExecutionTrace(task_id=f"t-{i}", objective="test", strategy_genome_hash="abc")
            t.add_step(ExecutionStep(step_id=1, action="step1", outcome=StepOutcome.SUCCESS, tool_used="grep"))
            t.add_step(ExecutionStep(step_id=2, action="step2", outcome=StepOutcome.SUCCESS, tool_used="view"))
            t.finalize(StepOutcome.SUCCESS)
            traces.append(t)
            
        proposals = synth.synthesize(traces, [])
        combo_proposals = [p for p in proposals if "prefer_combo" in p.name]
        assert len(combo_proposals) == 1
        assert "grep_view" in combo_proposals[0].name


class TestMetaMetaController:
    def test_tunnel_vision_detection(self):
        controller = MetaMetaController()
        strategy = SearchStrategy(default_genome())
        
        from cortex.sica.meta_level import MetaLevel
        meta = MetaLevel(strategy)
        
        for i in range(6):
            meta._judgment_history.append(
                MetaJudgment(
                    trace_id=f"t-{i}",
                    failure_class=FailureClass.CASCADE_BLINDNESS,
                    is_meta_failure=True,
                    confidence=0.9,
                    diagnosis="stuck",
                )
            )
            
        diagnoses = controller.check_and_correct(meta, strategy)
        assert len(diagnoses) == 1
        assert diagnoses[0].pattern == "tunnel_vision"
        assert strategy.genome.exploration_rate > 0.3


class TestAdaptiveRetry:
    def test_retry_on_constitutional_abort(self):
        ar = AdaptiveRetry(base_budget=3)
        from cortex.sica.constitution import ConstitutionalVerdict
        judgment = MetaJudgment(
            trace_id="t1",
            failure_class=None,
            is_meta_failure=False,
            confidence=0.9,
            diagnosis="constitutional issue",
            constitutional_verdict=ConstitutionalVerdict(passed=False, score=0.0, abort_needed=True, revision_needed=False)
        )
        assert ar.compute_budget(judgment) == 0

    def test_retry_on_meta_failure(self):
        ar = AdaptiveRetry(base_budget=3)
        judgment = MetaJudgment(
            trace_id="t2",
            failure_class=FailureClass.CASCADE_BLINDNESS,
            is_meta_failure=True,
            confidence=0.8,
            diagnosis="cascade",
        )
        budget = ar.compute_budget(judgment)
        assert budget > 3


class TestAutonomousTick:
    def test_should_tick_cooldown(self):
        tick = AutonomousTick(min_interval_s=5.0)
        # Set _last_tick to current time to ensure cooldown holds
        tick._last_tick = time.monotonic()
        assert tick.should_tick() is False
        # Move back in time to trigger tick
        tick._last_tick = time.monotonic() - 6.0
        assert tick.should_tick() is True


# ─── Strategy Persistence Tests ──────────────────────────────────────


class TestStrategyPersistence:
    @pytest.fixture
    def sica_dir(self, tmp_path):
        d = tmp_path / "sica"
        d.mkdir()
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def test_genome_json_roundtrip(self):
        g = default_genome()
        serialized = genome_to_json(g)
        deserialized = genome_from_json(serialized)
        
        assert deserialized.generation == g.generation
        assert deserialized.exploration_rate == g.exploration_rate
        assert deserialized.tool_priority == g.tool_priority
        assert len(deserialized.heuristics) == len(g.heuristics)
        assert deserialized.genome_hash == g.genome_hash

    def test_save_and_load_latest(self, sica_dir):
        g = default_genome()
        agent_id = "test_agent_1"
        
        path = save_genome(g, agent_id=agent_id, directory=sica_dir)
        assert path.exists()
        
        loaded = load_genome(agent_id=agent_id, directory=sica_dir)
        assert loaded is not None
        assert loaded.genome_hash == g.genome_hash
        
        strategy = load_or_default(agent_id=agent_id, directory=sica_dir)
        assert strategy.genome.genome_hash == g.genome_hash

    def test_load_or_default_fresh(self, sica_dir):
        strategy = load_or_default(agent_id="nonexistent_agent", directory=sica_dir)
        assert strategy.genome.generation == 0
        assert len(strategy.genome.heuristics) >= 4

    def test_list_generations(self, sica_dir):
        agent_id = "test_agent_generations"
        g = default_genome()
        
        save_genome(g, agent_id=agent_id, directory=sica_dir)
        
        g.generation = 1
        save_genome(g, agent_id=agent_id, directory=sica_dir)
        
        gens = list_generations(agent_id=agent_id, directory=sica_dir)
        assert len(gens) == 2
        assert gens[0]["generation"] == 0
        assert gens[1]["generation"] == 1
