from cortex.engine.membrane import Action, MembraneState, SovereignMembrane


def test_membrane_density_reject():
    membrane = SovereignMembrane(min_density=10)
    result = membrane.evaluate("too short", "general")
    assert result.action == Action.REJECT
    assert "low_physical_density" in result.diagnostic.reasons

def test_membrane_exergy_degrade():
    membrane = SovereignMembrane(exergy_threshold=0.40)
    # Content with decorative markers should have lower exergy
    content = "Por supuesto, aquí tienes la información. Espero que te sea útil en tu día a día."
    result = membrane.evaluate(content, "decision")
    assert result.action == Action.DEGRADE
    assert result.diagnostic.state == MembraneState.DECORATIVE

def test_membrane_behavioral_quarantine():
    membrane = SovereignMembrane(max_tool_fails=2)
    content = "High quality content with enough density to pass physical checks."
    counters = {"consecutive_tool_fails": 3}

    # Low exergy + bad behavior = Quarantine
    poor_content = "Ok, I will do it now. Just a moment please."
    result = membrane.evaluate(poor_content, "decision", counters=counters)

    assert result.diagnostic.state == MembraneState.QUARANTINED
    assert result.action == Action.REJECT

def test_membrane_admit_high_quality():
    membrane = SovereignMembrane()
    content = "The OAXACA membrane implements a unified O(1) entry point for cognitive induction."
    result = membrane.evaluate(content, "analysis")
    assert result.action == Action.ADMIT
    assert result.diagnostic.exergy_score > 0.40
