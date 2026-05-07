"""Admission tests for store provenance and taint requirements."""

from __future__ import annotations

import pytest

from cortex.engine.storage_guard import GuardViolation, StorageGuard
from cortex.guards.scrape_guard import CORTEX_TAINT_SIGNATURE


def test_canonical_storage_guard_rejects_missing_source() -> None:
    with pytest.raises(GuardViolation, match="SOURCE_REQUIRED"):
        StorageGuard.validate(
            project="provenance",
            content="A persisted fact needs explicit source attribution.",
            fact_type="knowledge",
            source=None,
        )


def test_external_api_source_requires_cortex_taint() -> None:
    with pytest.raises(GuardViolation, match="PROVENANCE_TAINT_REQUIRED"):
        StorageGuard.validate(
            project="provenance",
            content="External API payload cannot be admitted as clean fact.",
            fact_type="knowledge",
            source="api:external",
            meta={},
        )


def test_scrape_source_accepts_scrape_guard_taint() -> None:
    StorageGuard.validate(
        project="provenance",
        content="Scraped payload admitted only with explicit taint metadata.",
        fact_type="knowledge",
        source="scrape:firecrawl",
        meta={"cortex_taint": CORTEX_TAINT_SIGNATURE},
    )


def test_generative_source_requires_taint() -> None:
    with pytest.raises(GuardViolation, match="PROVENANCE_TAINT_REQUIRED"):
        StorageGuard.validate(
            project="provenance",
            content="LLM generated output remains conjecture until admitted with provenance.",
            fact_type="knowledge",
            source="llm:gpt",
            meta={},
        )


def test_generative_source_cannot_be_verified_without_deterministic_validation() -> None:
    with pytest.raises(GuardViolation, match="DETERMINISTIC_VALIDATION_REQUIRED"):
        StorageGuard.validate(
            project="provenance",
            content="LLM generated output cannot become verified fact by label alone.",
            fact_type="knowledge",
            source="llm:gpt",
            confidence="verified",
            meta={"cortex_taint": CORTEX_TAINT_SIGNATURE},
        )


def test_generative_source_accepts_verified_confidence_after_validation() -> None:
    StorageGuard.validate(
        project="provenance",
        content="LLM generated output with deterministic validation evidence.",
        fact_type="knowledge",
        source="llm:gpt",
        confidence="verified",
        meta={
            "cortex_taint": CORTEX_TAINT_SIGNATURE,
            "deterministic_validation": True,
        },
    )


def test_internal_agent_source_does_not_require_external_taint() -> None:
    StorageGuard.validate(
        project="provenance",
        content="Internal deterministic agent evidence can use normal attribution.",
        fact_type="knowledge",
        source="agent:test-suite",
        meta={},
    )
