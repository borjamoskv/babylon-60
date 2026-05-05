from __future__ import annotations

from cortex.compliance.dora.claim_policy import scan_text_for_claims


def test_claim_policy_detects_prohibited_claim() -> None:
    findings = scan_text_for_claims("This product is DORA compliant.")

    assert len(findings) == 1
    assert findings[0].term == "DORA compliant"
    assert not findings[0].conditional


def test_claim_policy_detects_bank_production_overclaim() -> None:
    findings = scan_text_for_claims("This package is bank-production ready.")

    assert len(findings) == 1
    assert findings[0].term == "bank-production ready"
    assert not findings[0].conditional


def test_claim_policy_detects_ai_act_default_compliance_overclaim() -> None:
    findings = scan_text_for_claims("CORTEX is EU AI Act compliant by default.")

    assert len(findings) == 1
    assert findings[0].term == "EU AI Act compliant by default"
    assert not findings[0].conditional


def test_claim_policy_detects_conditional_claim() -> None:
    findings = scan_text_for_claims("This deployment is EU-only.")

    assert len(findings) == 1
    assert findings[0].term == "EU-only"
    assert findings[0].conditional


def test_claim_policy_can_skip_conditional_terms() -> None:
    findings = scan_text_for_claims("This deployment is EU-only.", include_conditional=False)

    assert findings == []


def test_claim_policy_allows_explicit_line_suppression() -> None:
    findings = scan_text_for_claims(
        "Policy example: DORA certified. <!-- claim-policy: allow -->"
    )

    assert findings == []
