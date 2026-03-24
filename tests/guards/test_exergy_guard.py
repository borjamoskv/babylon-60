import pytest

from cortex.guards.exergy_guard import ExergyGuard


def test_exergy_guard_normal() -> None:
    guard = ExergyGuard()
    # High quality text
    score = guard.check_thermodynamic_yield("This is a highly factual sentence about system state.", "proj_1")
    assert score == 1.0

    # Low quality text
    with pytest.raises(ValueError, match="Thermodynamic Violation"):
        guard.check_thermodynamic_yield("Hi there! Como un modelo de lenguaje, estoy aquí para ayudarte.", "proj_1")

def test_exergy_guard_moltbook_wild() -> None:
    guard = ExergyGuard()
    # High quality text passes even with taint
    score = guard.check_thermodynamic_yield("This is a highly factual sentence about system state.", "proj_1", taint="MOLTBOOK_WILD")
    assert score == 1.0

    # Borderline text fails with MOLTBOOK_WILD (threshold 0.8)
    # 2 expressions * 0.2 penalty = 0.6 score. For normal it's > 0.5 (passes). For MOLTBOOK_WILD < 0.8 (fails).
    text = "Entendido, aquí tienes la información técnica requerida con precision absoluta."
    # Let's verify normal passes
    assert guard.check_thermodynamic_yield(text, "proj_1") == 0.6

    with pytest.raises(ValueError, match="Thermodynamic Violation"):
        guard.check_thermodynamic_yield(text, "proj_1", taint="MOLTBOOK_WILD")
