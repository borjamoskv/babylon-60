from cortex.extensions.gate.core import SovereignGate
from cortex.extensions.gate.enums import ActionLevel, GatePolicy, OversightState
from cortex.extensions.gate.errors import GateNotApproved, GateUnauthorizedReviewer


def _new_gate() -> SovereignGate:
    return SovereignGate(policy=GatePolicy.ENFORCE, secret="test-secret", timeout=300)


def test_high_risk_action_requires_human_review_before_final_effect() -> None:
    gate = _new_gate()
    action = gate.request_approval(
        level=ActionLevel.L4_MUTATE,
        description="Apply high-risk lending decision",
        command=["python3", "-c", "print('ok')"],
        project="banking",
        context={"taint": "tainted", "event_context": {"decision_id": "dec-001"}},
        high_risk=True,
        limitations=["model recommendation only"],
        provenance={"reason_codes": ["THALAMUS_REJECT", "LOW_CONFIDENCE"]},
    )

    assert action.oversight_state is OversightState.REVIEW_REQUIRED
    assert action.requires_human_review is True

    try:
        gate.execute_subprocess(action.action_id, ["python3", "-c", "print('ok')"], capture_output=True, text=True)
    except GateNotApproved:
        pass
    else:
        raise AssertionError("high-risk action executed without human review")

    approved = gate.approve(
        action.action_id,
        signature=action.hmac_challenge,
        operator_id="reviewer-1",
        reviewer_role="risk_officer",
        reason_code="MANUAL_REVIEW_ACCEPTED",
        auth_method="webauthn",
        strong_auth_token="webauthn-assertion-001",
    )
    assert approved is True

    result = gate.execute_subprocess(
        action.action_id,
        ["python3", "-c", "print('ok')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    persisted = gate._get_action(action.action_id)
    assert persisted.oversight_state is OversightState.FINAL_EFFECT_EXECUTED
    assert persisted.reviewer_role == "risk_officer"
    assert persisted.reason_code == "MANUAL_REVIEW_ACCEPTED"
    assert persisted.limitations == ["model recommendation only"]
    assert persisted.provenance["reason_codes"] == ["THALAMUS_REJECT", "LOW_CONFIDENCE"]


def test_high_risk_review_requires_authorized_role_and_reason_code() -> None:
    gate = _new_gate()
    action = gate.request_approval(
        level=ActionLevel.L4_MUTATE,
        description="Finalize adverse customer action",
        high_risk=True,
    )

    try:
        gate.approve(
            action.action_id,
            signature=action.hmac_challenge,
            operator_id="reviewer-2",
            reviewer_role="intern",
            reason_code="MANUAL_REVIEW_ACCEPTED",
        )
    except GateUnauthorizedReviewer:
        pass
    else:
        raise AssertionError("unauthorized reviewer role should be rejected")

    try:
        gate.approve(
            action.action_id,
            signature=action.hmac_challenge,
            operator_id="reviewer-2",
            reviewer_role="risk_officer",
        )
    except GateUnauthorizedReviewer:
        pass
    else:
        raise AssertionError("missing reason_code should be rejected")


def test_high_risk_override_is_audited_and_enables_execution() -> None:
    gate = _new_gate()
    action = gate.request_approval(
        level=ActionLevel.L3_EXECUTE,
        description="Release disputed payment block",
        command=["python3", "-c", "print('override')"],
        high_risk=True,
    )

    overridden = gate.override(
        action.action_id,
        signature=action.hmac_challenge,
        operator_id="reviewer-3",
        reviewer_role="compliance_officer",
        reason_code="OVERRIDE_CASE_REOPENED",
        auth_method="webauthn",
        strong_auth_token="webauthn-assertion-002",
    )
    assert overridden is True

    persisted = gate._get_action(action.action_id)
    assert persisted.oversight_state is OversightState.HUMAN_OVERRIDE
    assert persisted.override_reason_code == "OVERRIDE_CASE_REOPENED"

    result = gate.execute_subprocess(
        action.action_id,
        ["python3", "-c", "print('override')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert gate._get_action(action.action_id).oversight_state is OversightState.FINAL_EFFECT_EXECUTED
