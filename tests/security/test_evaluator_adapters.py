# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

"""Tests for CORTEX security evaluator adapters."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.extensions.security.evaluator_adapters import (
    EvaluationResult,
    IntentValidationAdapter,
    StoreValidationAdapter,
    ThalamusGateAdapter,
    URLGuardAdapter,
    ZKGuardAdapter,
)


@pytest.fixture
def mock_thalamus_gate():
    gate = MagicMock()
    gate.filter = AsyncMock()
    return gate


@pytest.fixture
def mock_intent_validator():
    validator = MagicMock()
    return validator


@pytest.fixture
def mock_zk_guard():
    guard = MagicMock()
    guard.verify_integrity = AsyncMock()
    return guard


def test_evaluation_result():
    res = EvaluationResult(
        decision="allow", reason_code="test.ok", reason="All fine", meta={"x": 1}
    )
    assert res.decision == "allow"
    assert res.reason_code == "test.ok"
    assert res.reason == "All fine"
    assert res.meta == {"x": 1}
    assert res.to_dict() == {
        "decision": "allow",
        "reason_code": "test.ok",
        "reason": "All fine",
        "meta": {"x": 1},
    }

    with pytest.raises(ValueError):
        EvaluationResult(decision="invalid_decision", reason_code="test.bad")


class TestStoreValidationAdapter:
    @pytest.mark.asyncio
    async def test_store_validation_success(self):
        adapter = StoreValidationAdapter()
        with patch(
            "cortex.engine.store_validation.run_store_validation_logic",
            new_callable=AsyncMock,
        ) as mock_logic:
            mock_logic.return_value = (None, {"updated": True}, "resolved content", "fact_type")
            res = await adapter.evaluate(
                mixin_instance=None,
                conn=None,
                project="proj",
                content="content",
                tenant_id="tenant",
                fact_type="general",
            )
            assert res.decision == "allow"
            assert res.reason_code == "store.validated"
            assert res.meta["resolved_content"] == "resolved content"

    @pytest.mark.asyncio
    async def test_store_validation_duplicate(self):
        adapter = StoreValidationAdapter()
        with patch(
            "cortex.engine.store_validation.run_store_validation_logic",
            new_callable=AsyncMock,
        ) as mock_logic:
            mock_logic.return_value = (42, {"updated": True}, "resolved content", "fact_type")
            res = await adapter.evaluate(
                mixin_instance=None,
                conn=None,
                project="proj",
                content="content",
                tenant_id="tenant",
                fact_type="general",
            )
            assert res.decision == "allow"
            assert res.reason_code == "store.duplicate_detected"
            assert res.meta["duplicate_id"] == 42

    @pytest.mark.asyncio
    async def test_store_validation_byzantine_auth_fail(self):
        adapter = StoreValidationAdapter()
        with patch(
            "cortex.engine.store_validation.run_store_validation_logic",
            new_callable=AsyncMock,
        ) as mock_logic:
            mock_logic.side_effect = PermissionError("byzantine signature invalid")
            res = await adapter.evaluate(
                mixin_instance=None,
                conn=None,
                project="proj",
                content="content",
                tenant_id="tenant",
                fact_type="general",
            )
            assert res.decision == "block"
            assert res.reason_code == "store.byzantine_auth_failed"

    @pytest.mark.asyncio
    async def test_store_validation_guard_blocked(self):
        adapter = StoreValidationAdapter()
        with patch(
            "cortex.engine.store_validation.run_store_validation_logic",
            new_callable=AsyncMock,
        ) as mock_logic:
            mock_logic.side_effect = ValueError(
                "SECURITY GUARD BLOCK [injection_guard]: unsafe code pattern detected"
            )
            res = await adapter.evaluate(
                mixin_instance=None,
                conn=None,
                project="proj",
                content="content",
                tenant_id="tenant",
                fact_type="general",
            )
            assert res.decision == "block"
            assert res.reason_code == "store.guard_blocked.injection_guard"

    @pytest.mark.asyncio
    async def test_store_validation_unexpected_error(self):
        adapter = StoreValidationAdapter()
        with patch(
            "cortex.engine.store_validation.run_store_validation_logic",
            new_callable=AsyncMock,
        ) as mock_logic:
            mock_logic.side_effect = Exception("General database collapse")
            res = await adapter.evaluate(
                mixin_instance=None,
                conn=None,
                project="proj",
                content="content",
                tenant_id="tenant",
                fact_type="general",
            )
            assert res.decision == "error"
            assert res.reason_code == "store.unexpected_error"


class TestThalamusGateAdapter:
    @pytest.mark.asyncio
    async def test_thalamus_allow(self, mock_thalamus_gate):
        mock_thalamus_gate.filter.return_value = (True, "accept:high_density", {"score": 0.9})
        adapter = ThalamusGateAdapter(mock_thalamus_gate)
        res = await adapter.evaluate(content="hello", project_id="proj", tenant_id="tenant")
        assert res.decision == "allow"
        assert res.reason_code == "thalamus.allow"
        assert res.meta["action"] == "accept:high_density"

    @pytest.mark.asyncio
    async def test_thalamus_block_discard(self, mock_thalamus_gate):
        mock_thalamus_gate.filter.return_value = (False, "discard:low_density", {"score": 0.1})
        adapter = ThalamusGateAdapter(mock_thalamus_gate)
        res = await adapter.evaluate(
            content="low quality content", project_id="proj", tenant_id="tenant"
        )
        assert res.decision == "block"
        assert res.reason_code == "thalamus.block.low_density"
        assert res.meta["action"] == "discard:low_density"

    @pytest.mark.asyncio
    async def test_thalamus_error_path(self, mock_thalamus_gate):
        mock_thalamus_gate.filter.side_effect = Exception("Thalamus database lock")
        adapter = ThalamusGateAdapter(mock_thalamus_gate)
        res = await adapter.evaluate(content="content", project_id="proj", tenant_id="tenant")
        assert res.decision == "error"
        assert res.reason_code == "thalamus.error"


class TestIntentValidationAdapter:
    @pytest.mark.asyncio
    async def test_intent_aligned(self, mock_intent_validator):
        from cortex.extensions.llm._models import IntentProfile
        from cortex.extensions.llm._validation import DriftSignal

        drift = DriftSignal(
            provider="test-prov",
            requested_intent=IntentProfile.CODE,
            detected_intent=IntentProfile.CODE,
            confidence=0.8,
            is_drift=False,
            evidence="Matched perfectly",
        )
        mock_intent_validator.validate.return_value = drift
        adapter = IntentValidationAdapter(mock_intent_validator)

        res = await adapter.evaluate("def test(): pass", "code")
        assert res.decision == "allow"
        assert res.reason_code == "intent.aligned"

    @pytest.mark.asyncio
    async def test_intent_drift_detected(self, mock_intent_validator):
        from cortex.extensions.llm._models import IntentProfile
        from cortex.extensions.llm._validation import DriftSignal

        drift = DriftSignal(
            provider="test-prov",
            requested_intent=IntentProfile.CODE,
            detected_intent=IntentProfile.CREATIVE,
            confidence=0.9,
            is_drift=True,
            evidence="Drift detected: creative text returned instead of code",
        )
        mock_intent_validator.validate.return_value = drift
        adapter = IntentValidationAdapter(mock_intent_validator)

        res = await adapter.evaluate("Once upon a time in a faraway valley...", "code")
        assert res.decision == "block"
        assert res.reason_code == "intent.drift_detected"
        assert res.meta["detected_intent"] == "creative"


class TestURLGuardAdapter:
    @pytest.mark.asyncio
    async def test_url_safe(self):
        adapter = URLGuardAdapter()
        with patch("cortex.guards.url_guard.is_safe_url", return_value=True):
            res = await adapter.evaluate("https://google.com")
            assert res.decision == "allow"
            assert res.reason_code == "url.safe"

    @pytest.mark.asyncio
    async def test_url_unsafe(self):
        adapter = URLGuardAdapter()
        with patch("cortex.guards.url_guard.is_safe_url", return_value=False):
            res = await adapter.evaluate("http://localhost/admin")
            assert res.decision == "block"
            assert res.reason_code == "url.unsafe"


class TestZKGuardAdapter:
    @pytest.mark.asyncio
    async def test_zk_verified(self, mock_zk_guard):
        mock_zk_guard.verify_integrity.return_value = None
        adapter = ZKGuardAdapter(mock_zk_guard)

        res = await adapter.evaluate(
            "content",
            "decision",
            {"agent_public_key": "abc", "zk_proof_signature": "123"},
        )
        assert res.decision == "allow"
        assert res.reason_code == "zk.verified"

    @pytest.mark.asyncio
    async def test_zk_proof_invalid(self, mock_zk_guard):
        from cortex.guards.zk_guard import VoidStateSecurityError

        mock_zk_guard.verify_integrity.side_effect = VoidStateSecurityError(
            "Invalid proof signature"
        )
        adapter = ZKGuardAdapter(mock_zk_guard)

        res = await adapter.evaluate(
            "content",
            "decision",
            {"agent_public_key": "abc", "zk_proof_signature": "bad"},
        )
        assert res.decision == "block"
        assert res.reason_code == "zk.proof_invalid"
