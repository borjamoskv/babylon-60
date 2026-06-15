# [C5-REAL] Exergy-Maximized
"""Tests for ARCHITECT-Ω agent loading and validation."""

from cortex.extensions.agents.registry import AgentRegistry


def test_architect_agent_loading():
    """Verify that ARCHITECT-Ω YAML exists, is parsed, and is registered correctly."""
    registry = AgentRegistry()
    registry.clear()
    # Loading default production definitions
    registry.load_all()

    # Retrieve architect agent
    architect = registry.get("architect")
    assert architect is not None, "ARCHITECT-Ω agent was not registered"

    # Validate top-level schema attributes
    assert architect.name == "ARCHITECT-Ω"
    assert architect.model == "gemini-3.1-pro-preview"
    assert architect.provider == "gemini"
    assert architect.intent == "architect"
    assert architect.tenant_id == "default"
    assert architect.project_id == "system"

    # Validate memory configuration
    assert float(architect.memory.art_rho) == 0.98
    assert float(architect.memory.pruning_threshold) == 0.05
    assert architect.memory.retrieval_band == "beta"
    assert architect.memory.tier == "hot"
    assert architect.memory.sparse_encoding is True
    assert architect.memory.silent_engrams is False
    assert architect.memory.causal_memory is True

    # Validate guardrails
    assert architect.guardrails.max_session_tokens == 200000
    assert float(architect.guardrails.warn_threshold) == 0.85
    assert architect.guardrails.max_turns == 50

    # Validate tool coverage
    expected_tools = {
        "filesystem",
        "terminal",
        "mcp",
        "cortex_search",
        "cortex_store",
        "run_command",
        "list_dir",
        "view_file",
        "grep_search",
        "agentic_task_boundary",
        "crystallization_persist",
    }
    assert set(architect.tools) == expected_tools, "Tool definition mismatch"
    assert "You are ARCHITECT-Ω" in architect.system_prompt
