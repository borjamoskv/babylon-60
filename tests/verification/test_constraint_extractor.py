from __future__ import annotations

import pytest

from cortex.verification.extractor import SMTModelExtractor, extract_constraints


def test_extract_constraints_returns_empty_for_safe_code() -> None:
    code = """
total = 0
for item in [1, 2, 3]:
    total += item
"""

    assert extract_constraints(code) == []
    assert SMTModelExtractor(code).analyze() == []


@pytest.mark.parametrize("method_name", ["delete", "remove", "drop_table"])
def test_extract_constraints_flags_prohibited_attribute_calls(method_name: str) -> None:
    findings = extract_constraints(f"ledger.{method_name}('facts')")

    assert findings == [
        {
            "invariant_id": "I2",
            "message": f"Prohibited method call: {method_name}",
        }
    ]


def test_extract_constraints_flags_eval_calls() -> None:
    findings = extract_constraints("eval(user_input)")

    assert findings == [
        {
            "invariant_id": "I7",
            "message": "Prohibited use of 'eval' prevents termination analysis.",
        }
    ]


def test_extract_constraints_returns_syntax_finding_for_invalid_python() -> None:
    findings = extract_constraints("def broken(:")

    assert findings[0]["invariant_id"] == "SYNTAX"
    assert "Code parsing failed" in findings[0]["message"]
