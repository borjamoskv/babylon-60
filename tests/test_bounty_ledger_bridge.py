"""Tests for cortex.bounty.ledger_bridge — BountyLedgerBridge integration."""
from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from cortex.bounty.ledger_bridge import BountyLedgerBridge
from cortex.bounty.models import BountyFinding, BountyPlatform, Confidence


@pytest_asyncio.fixture
async def bridge(tmp_path: Path) -> BountyLedgerBridge:
    db = tmp_path / "test_cortex.db"
    return BountyLedgerBridge(db_path=db)


@pytest.mark.asyncio
async def test_seal_single_finding(bridge: BountyLedgerBridge) -> None:
    finding = {
        "vector_id": "SKY-Σ1-DUST",
        "protocol": "sky",
        "confidence": "C5-Deterministic",
        "finding": "Integer truncation in buyGemNoFee traps dust permanently.",
        "seal": "f440610c7d57b75b",
    }
    event_id = await bridge.seal(finding, session_id="test-session-001")
    assert event_id is not None
    assert len(event_id) > 0  # non-empty ID


@pytest.mark.asyncio
async def test_chain_integrity_after_multiple_seals(bridge: BountyLedgerBridge) -> None:
    findings = [
        {
            "vector_id": "SKY-Σ1-DUST",
            "protocol": "sky",
            "confidence": "C5-Deterministic",
            "finding": "Dust trap in SwapperCalleePsm",
            "seal": "aaa111",
        },
        {
            "vector_id": "SSV-Σ3-FEE-DOS",
            "protocol": "ssv",
            "confidence": "C4-Strong",
            "finding": "uint64 overflow DoS in OperatorLib.updateSnapshot",
            "seal": "bbb222",
        },
    ]
    for f in findings:
        await bridge.seal(f, session_id="test-session-002")

    audit = await bridge.verify_integrity()
    assert audit["status"] == "VALID"
    assert audit["events_audited"] == 2
    assert audit["integrity_score"] == 1.0


@pytest.mark.asyncio
async def test_get_all_findings_returns_correct_count(bridge: BountyLedgerBridge) -> None:
    for i in range(3):
        await bridge.seal(
            {
                "vector_id": f"TEST-Σ{i}",
                "protocol": "test",
                "confidence": "C3-Hypothetical",
                "finding": f"Finding {i}",
                "seal": f"seal{i}",
            },
            session_id="test-session-003",
        )

    all_findings = await bridge.get_all_findings(session_id="test-session-003")
    assert len(all_findings) == 3


@pytest.mark.asyncio
async def test_finding_content_is_recoverable(bridge: BountyLedgerBridge) -> None:
    original = {
        "vector_id": "SKY-Σ1-DUST",
        "protocol": "sky",
        "confidence": "C5-Deterministic",
        "finding": "Dust trap in SwapperCalleePsm — no sweep function exists.",
        "seal": "f440610c7d57b75b",
        "code_evidence": "L67-68: constraint intentionally not enforced.",
    }
    await bridge.seal(original, session_id="test-session-004")

    recovered = await bridge.get_all_findings(session_id="test-session-004")
    assert len(recovered) == 1
    content = recovered[0]["content"]
    assert content["vector_id"] == "SKY-Σ1-DUST"
    assert content["seal"] == "f440610c7d57b75b"


@pytest.mark.asyncio
async def test_count_findings(bridge: BountyLedgerBridge) -> None:
    assert await bridge.count_findings() == 0
    await bridge.seal(
        {
            "vector_id": "X-1",
            "protocol": "test",
            "confidence": "C4-Strong",
            "finding": "test",
            "seal": "abc",
        },
        session_id="count-test",
    )
    assert await bridge.count_findings() == 1


@pytest.mark.asyncio
async def test_pydantic_model_integration(bridge: BountyLedgerBridge) -> None:
    finding_model = BountyFinding(
        vector_id="SSV-Σ3-FEE-DOS",
        protocol="ssv",
        contract="OperatorLib.sol",
        function="updateSnapshot()",
        confidence=Confidence.C4_STRONG,
        finding="uint64 overflow in blockDiffFee causes permanent operator DoS",
        severity="medium",
        bounty_platform=BountyPlatform.IMMUNEFI,
        max_bounty_usd=1_000_000,
        code_evidence="L14-20: (uint32(block.number) - operator.snapshot.block) * operator.fee",
        poc_path="foundry/test/SSVFeeOverflow.t.sol",
        seal="ssv_seal_001",
    )
    event_id = await bridge.seal(finding_model.to_ledger_dict(), session_id="model-test")
    assert event_id is not None

    audit = await bridge.verify_integrity()
    assert audit["status"] == "VALID"
