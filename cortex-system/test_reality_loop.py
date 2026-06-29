"""
C5-REAL: Adversarial Test Suite for Reality Loop
Author: Borja Moskv / borjamoskv
"""

import sys
import os
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from reality_loop import mutate_reward_model
from policies.abort_rules import AbortRules

def test_ast_mutation_safeguards():
    """
    Simulates extreme system fatigue and entropy to ensure the AST mutator
    correctly bounds thresholds and commits safely without syntactical collapse.
    """
    # 1. Extreme thermodynamic pressure
    metric = {
        "entropy": 0.01,
        "fatigue": 0.99
    }
    
    # 2. Mutate (this will rewrite reward_model.py and commit)
    success = mutate_reward_model(metric)
    assert success is True, "AST Mutation failed or crashed"
    
    # 3. Import and verify new thresholds
    # We must reload because the file on disk changed
    import importlib
    import policies.reward_model
    importlib.reload(policies.reward_model)
    
    orig = policies.reward_model.ORIGINALITY_THRESHOLD
    dist = policies.reward_model.DISTRIBUTION_THRESHOLD
    
    assert orig >= 0.20 and orig <= 0.60, f"Originality {orig} out of bounds"
    assert dist >= 0.15 and dist <= 0.40, f"Distribution {dist} out of bounds"

def test_abort_rules_boundaries():
    """
    Validates that the abort rules intercept invalid states (Rule R3/R9).
    """
    fatal_metrics = {
        "originality_raw": 0.15, # Below 0.20
        "friction_ms": 1000,
        "attention_yield": 0.50
    }
    
    result = AbortRules.evaluate(fatal_metrics)
    assert result["abort"] is True
    assert "Originality ratio" in result["reason"]
    
    stall_metrics = {
        "originality_raw": 0.50,
        "friction_ms": 200000, # Exceeds 180000
        "attention_yield": 0.50
    }
    
    result = AbortRules.evaluate(stall_metrics)
    assert result["abort"] is True
    assert "Execution friction" in result["reason"]
