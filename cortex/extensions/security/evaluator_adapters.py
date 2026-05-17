# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

"""Sovereign Guard Evaluator Adapters (RFC-CORTEX-NATIVE-AI).

Normalizes different CORTEX security & validation surfaces to a uniform
allow/block/error decision interface with stable reason codes.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

logger = logging.getLogger("cortex.security.evaluators")


class EvaluationResult:
    """Standardized decision container for all evaluator adapters."""

    def __init__(
        self,
        decision: str,  # "allow", "block", "error"
        reason_code: str,
        reason: str | None = None,
        meta: dict[str, Any] | None = None,
    ):
        if decision not in {"allow", "block", "error"}:
            raise ValueError(f"Invalid evaluation decision: {decision}")
        self.decision = decision
        self.reason_code = reason_code
        self.reason = reason
        self.meta = meta or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "meta": self.meta,
        }

    def __repr__(self) -> str:
        return (
            f"EvaluationResult(decision={self.decision!r}, "
            f"reason_code={self.reason_code!r}, reason={self.reason!r})"
        )


class GuardEvaluatorAdapter(Protocol):
    """Formal protocol for all guard evaluator adapters."""

    async def evaluate(self, *args: Any, **kwargs: Any) -> EvaluationResult: ...


class StoreValidationAdapter:
    """Adapter for the core store_validation pipeline logic."""

    async def evaluate(
        self,
        mixin_instance: Any,
        conn: Any,
        project: str,
        content: str,
        tenant_id: str,
        fact_type: str,
        tags: list[str] | None = None,
        confidence: str = "high",
        source: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        try:
            from cortex.engine.store_validation import run_store_validation_logic

            (
                duplicate_id,
                updated_meta,
                resolved_content,
                resolved_type,
            ) = await run_store_validation_logic(
                mixin_instance=mixin_instance,
                conn=conn,
                project=project,
                content=content,
                tenant_id=tenant_id,
                fact_type=fact_type,
                tags=tags,
                confidence=confidence,
                source=source,
                meta=meta,
            )

            if duplicate_id is not None:
                return EvaluationResult(
                    decision="allow",
                    reason_code="store.duplicate_detected",
                    reason=f"Duplicate fact detected: {duplicate_id}",
                    meta={
                        "duplicate_id": duplicate_id,
                        "resolved_content": resolved_content,
                        "resolved_type": resolved_type,
                    },
                )

            return EvaluationResult(
                decision="allow",
                reason_code="store.validated",
                reason="Store validation passed successfully.",
                meta={
                    "meta": updated_meta,
                    "resolved_content": resolved_content,
                    "resolved_type": resolved_type,
                },
            )

        except PermissionError as e:
            return EvaluationResult(
                decision="block",
                reason_code="store.byzantine_auth_failed",
                reason=str(e),
            )
        except ValueError as e:
            reason_str = str(e)
            reason_code = "store.validation_failed"
            if "SECURITY GUARD BLOCK" in reason_str:
                for guard_name in [
                    "injection_guard",
                    "honeypot_guard",
                    "contradiction_signal_guard",
                    "bridge_conflict_guard",
                    "anomaly_guard",
                ]:
                    if guard_name in reason_str:
                        reason_code = f"store.guard_blocked.{guard_name}"
                        break
            return EvaluationResult(
                decision="block",
                reason_code=reason_code,
                reason=reason_str,
            )
        except RuntimeError as e:
            if "DECORATIVE mode" in str(e):
                return EvaluationResult(
                    decision="block",
                    reason_code="store.decorative_mode_blocked",
                    reason=str(e),
                )
            return EvaluationResult(
                decision="error",
                reason_code="store.runtime_error",
                reason=str(e),
            )
        except Exception as e:
            return EvaluationResult(
                decision="error",
                reason_code="store.unexpected_error",
                reason=str(e),
            )


class ThalamusGateAdapter:
    """Adapter for normalizing ThalamusGate filtering decisions."""

    def __init__(self, thalamus_gate: Any) -> None:
        self._gate = thalamus_gate

    async def evaluate(
        self,
        content: str,
        project_id: str,
        tenant_id: str,
        fact_type: str = "general",
        parent_decision_id: int | None = None,
        conn: Any = None,
    ) -> EvaluationResult:
        try:
            should_process, action_taken, metadata_patch = await self._gate.filter(
                content=content,
                project_id=project_id,
                tenant_id=tenant_id,
                fact_type=fact_type,
                parent_decision_id=parent_decision_id,
                conn=conn,
            )

            if should_process:
                return EvaluationResult(
                    decision="allow",
                    reason_code="thalamus.allow",
                    reason=f"Action: {action_taken}",
                    meta={"action": action_taken, "metadata_patch": metadata_patch},
                )

            # Extract sub-action from action_taken (e.g. discard:low_density -> low_density)
            sub_code = "filtered"
            if action_taken and ":" in action_taken:
                parts = action_taken.split(":", 1)
                sub_code = parts[1] if parts[1] else parts[0]
            elif action_taken:
                sub_code = action_taken

            return EvaluationResult(
                decision="block",
                reason_code=f"thalamus.block.{sub_code}",
                reason=f"Thalamus filtered out fact: {action_taken}",
                meta={"action": action_taken, "metadata_patch": metadata_patch},
            )
        except Exception as e:
            return EvaluationResult(
                decision="error",
                reason_code="thalamus.error",
                reason=str(e),
            )


class IntentValidationAdapter:
    """Adapter for verifying provider responses against expected semantic intents."""

    def __init__(self, intent_validator: Any = None) -> None:
        if intent_validator is not None:
            self._validator = intent_validator
        else:
            try:
                from cortex.extensions.llm._validation import IntentValidator

                self._validator = IntentValidator()
            except ImportError:
                self._validator = None

    async def evaluate(
        self,
        response: str,
        requested_intent: Any,  # IntentProfile or str
        provider_name: str = "unknown",
    ) -> EvaluationResult:
        if self._validator is None:
            return EvaluationResult(
                decision="error",
                reason_code="intent.dependency_missing",
                reason="IntentValidator dependency is not installed.",
            )

        try:
            from cortex.extensions.llm._models import IntentProfile

            requested_profile = requested_intent
            if isinstance(requested_intent, str):
                try:
                    requested_profile = IntentProfile(requested_intent.lower())
                except ValueError:
                    requested_profile = IntentProfile.GENERAL

            drift_signal = self._validator.validate(response, requested_profile, provider_name)

            if drift_signal.is_drift:
                return EvaluationResult(
                    decision="block",
                    reason_code="intent.drift_detected",
                    reason=drift_signal.evidence,
                    meta={
                        "requested_intent": (
                            drift_signal.requested_intent.value
                            if hasattr(drift_signal.requested_intent, "value")
                            else str(drift_signal.requested_intent)
                        ),
                        "detected_intent": (
                            drift_signal.detected_intent.value
                            if hasattr(drift_signal.detected_intent, "value")
                            else str(drift_signal.detected_intent)
                        ),
                        "confidence": drift_signal.confidence,
                    },
                )

            return EvaluationResult(
                decision="allow",
                reason_code="intent.aligned",
                reason="Intent validation passed successfully.",
                meta={
                    "requested_intent": (
                        drift_signal.requested_intent.value
                        if hasattr(drift_signal.requested_intent, "value")
                        else str(drift_signal.requested_intent)
                    ),
                    "detected_intent": (
                        drift_signal.detected_intent.value
                        if hasattr(drift_signal.detected_intent, "value")
                        else str(drift_signal.detected_intent)
                    ),
                    "confidence": drift_signal.confidence,
                },
            )
        except Exception as e:
            return EvaluationResult(
                decision="error",
                reason_code="intent.error",
                reason=str(e),
            )


class URLGuardAdapter:
    """Adapter for outgoing outbound request URL validation (SSRF Protection)."""

    async def evaluate(self, url: str, allow_private: bool = False) -> EvaluationResult:
        try:
            from cortex.guards.url_guard import is_safe_url

            if is_safe_url(url, allow_private=allow_private):
                return EvaluationResult(
                    decision="allow",
                    reason_code="url.safe",
                    reason="URL is safe for outbound requests.",
                    meta={"url": url},
                )

            return EvaluationResult(
                decision="block",
                reason_code="url.unsafe",
                reason="URL failed safety check (SSRF or invalid scheme/host).",
                meta={"url": url},
            )
        except Exception as e:
            return EvaluationResult(
                decision="error",
                reason_code="url.error",
                reason=str(e),
                meta={"url": url},
            )


class ZKGuardAdapter:
    """Adapter for verifying ZK-Swarm consensus proofs."""

    def __init__(self, zk_guard: Any = None) -> None:
        if zk_guard is not None:
            self._guard = zk_guard
        else:
            try:
                from cortex.guards.zk_guard import ZKSwarmGuard

                self._guard = ZKSwarmGuard()
            except ImportError:
                self._guard = None

    async def evaluate(
        self,
        content: str,
        fact_type: str,
        meta: dict[str, Any],
    ) -> EvaluationResult:
        if self._guard is None:
            return EvaluationResult(
                decision="error",
                reason_code="zk.dependency_missing",
                reason="ZKSwarmGuard dependency is not installed.",
            )

        try:
            await self._guard.verify_integrity(content, fact_type, meta)
            return EvaluationResult(
                decision="allow",
                reason_code="zk.verified",
                reason="ZK proof verified successfully or fact type bypassed verification.",
            )
        except Exception as e:
            from cortex.guards.zk_guard import VoidStateSecurityError

            if isinstance(e, VoidStateSecurityError):
                return EvaluationResult(
                    decision="block",
                    reason_code="zk.proof_invalid",
                    reason=str(e),
                )
            return EvaluationResult(
                decision="error",
                reason_code="zk.error",
                reason=str(e),
            )
