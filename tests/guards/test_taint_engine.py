import pytest
from cortex.guards.taint_engine import CortexTaintEngine, SovereignValidator


def test_generate_taint():
    agent_id = "agent-omega"
    session_id = "session-xyz"
    payload = {"claim": "100 yield", "real": True}

    taint_token = CortexTaintEngine.generate_taint(agent_id, session_id, payload)

    assert taint_token.startswith(f"taint:{agent_id}:{session_id}:")
    parts = taint_token.split(":")
    assert len(parts) == 7
    # The last part must be a SHA-3-256 hash (64 hex characters)
    assert len(parts[-1]) == 64


def test_verify_taint_presence():
    fact = {
        "content": "Sovereign execution",
        "_cortex_taint": "taint:agent-omega:session-xyz:2026-05-18T11:00:00Z:hash",
    }
    assert CortexTaintEngine.verify_taint_presence(fact) is True

    fact_no_taint = {"content": "Sovereign execution"}
    assert CortexTaintEngine.verify_taint_presence(fact_no_taint) is False

    fact_invalid_taint = {"content": "Sovereign execution", "_cortex_taint": "invalid-taint-token"}
    assert CortexTaintEngine.verify_taint_presence(fact_invalid_taint) is False


def test_revoke_taint():
    fact = {
        "content": "Sovereign execution",
        "_cortex_taint": "taint:agent-omega:session-xyz:2026-05-18T11:00:00Z:hash",
    }
    revoked = CortexTaintEngine.revoke_taint(fact)
    assert "_cortex_taint" not in revoked


def test_sovereign_validator_empty():
    assert SovereignValidator.validate_mutation({}, "sig") is False


def test_sovereign_validator_unsigned():
    mutation = {"content": "Sovereign execution"}
    assert SovereignValidator.validate_mutation(mutation, "sig") is False


def test_sovereign_validator_success():
    mutation = {
        "content": "Sovereign execution",
        "_cortex_taint": "taint:agent-omega:session-xyz:2026-05-18T11:00:00Z:hash",
    }
    assert SovereignValidator.validate_mutation(mutation, "sig") is True
