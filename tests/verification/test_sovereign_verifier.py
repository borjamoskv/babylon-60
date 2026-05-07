from __future__ import annotations

from cortex.verification.invariants import SafetyInvariant
from cortex.verification.verifier import SovereignVerifier


def test_sovereign_verifier_accepts_code_without_ast_findings() -> None:
    result = SovereignVerifier().check("value = 1 + 1", context={"file_path": "safe.py"})

    assert result.is_valid is True
    assert result.violations == []
    assert result.proof_certificate == "Z3_UNSAT_BY_AST_PROXIMAL"
    assert result.counterexample is None


def test_sovereign_verifier_rejects_eval_with_named_invariant() -> None:
    verifier = SovereignVerifier(
        invariants=[
            SafetyInvariant(
                id="I7",
                name="Termination Guarantee",
                description="No unsafe dynamic execution.",
            )
        ]
    )

    result = verifier.check("eval(user_input)", context={"file_path": "mutation.py"})

    assert result.is_valid is False
    assert result.violations == [
        {
            "id": "I7",
            "name": "Termination Guarantee",
            "message": "Prohibited use of 'eval' prevents termination analysis.",
        }
    ]
    assert result.counterexample == {
        "findings": [
            {
                "invariant_id": "I7",
                "message": "Prohibited use of 'eval' prevents termination analysis.",
            }
        ],
        "file": "mutation.py",
    }


def test_sovereign_verifier_rejects_prohibited_mutation_methods() -> None:
    result = SovereignVerifier().check("ledger.delete(record_id)")

    assert result.is_valid is False
    assert result.violations[0]["id"] == "I2"
    assert result.violations[0]["name"] == "Ledger Append-Only"
    assert result.violations[0]["message"] == "Prohibited method call: delete"


def test_sovereign_verifier_reports_syntax_errors() -> None:
    result = SovereignVerifier().check("def broken(:", context={"file_path": "bad.py"})

    assert result.is_valid is False
    assert result.violations[0]["id"] == "SYNTAX"
    assert result.violations[0]["name"] == "SYNTAX"
    assert "Code parsing failed" in result.violations[0]["message"]
    assert result.counterexample["file"] == "bad.py"
