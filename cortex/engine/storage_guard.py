"""StorageGuard — Mandatory pre-store middleware.

No fact reaches the database without passing through this guard.
This is NOT opt-in. CortexEngine.store() calls it automatically.

Enforces:
1. Source attribution — every fact must have a source
2. Privacy classification — delegates to PrivacyMixin (blocks unclassified sensitive data)
3. Content integrity — size limits, poisoning detection (delegates to MCPGuard)
4. Fact type whitelist — only allowed types pass
5. Project validation — non-empty, reasonable length

Copyright 2026 by borjamoskv.com — Apache-2.0
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

__all__ = ["StorageGuard", "GuardViolation", "StoreProposal"]

logger = logging.getLogger("cortex.guard.storage")


class GuardViolation(Exception):
    """Raised when a store operation violates a mandatory guard rule."""

    def __init__(self, rule: str, detail: str) -> None:
        self.rule = rule
        self.detail = detail
        super().__init__(f"[{rule}] {detail}")


# ─── Allowed Values ────────────────────────────────────────────────

_ALLOWED_FACT_TYPES: frozenset[str] = frozenset(
    {
        "knowledge",
        "decision",
        "error",
        "ghost",
        "bridge",
        "preference",
        "identity",
        "issue",
        "world-model",
        "counterfactual",
        "rule",
        "axiom",
        "schema",
        "idea",
        "evolution",
        "test",
        "system_health",
        "analysis",
    }
)

_ALLOWED_CONFIDENCE: frozenset[str] = frozenset(
    {
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "stated",
        "inferred",
        "verified",
    }
)

_MAX_PROJECT_LENGTH = 256
_MAX_CONTENT_LENGTH = 500_000
_MAX_TAGS = 50
_MAX_TAG_LENGTH = 128
_MIN_CONTENT_LENGTH = 10
_TAINT_KEYS: frozenset[str] = frozenset(
    {"CORTEX-TAINT", "cortex-taint", "cortex_taint", "provenance_taint"}
)

# ─── Poisoning Patterns (shared with MCPGuard) ────────────────────

_POISON_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r";\s*DROP\s+TABLE", re.IGNORECASE),
    re.compile(r";\s*DELETE\s+FROM", re.IGNORECASE),
    re.compile(r"UNION\s+SELECT\s+", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an|DAN)", re.IGNORECASE),
    re.compile(r"__cortex_override__", re.IGNORECASE),
]


def _source_requires_taint(source: str) -> bool:
    """Return true when a source crosses an untrusted provenance boundary."""
    normalized = source.strip().casefold()
    if not normalized:
        return False
    if normalized in {"external", "scrape", "crawler", "firecrawl", "llm"}:
        return True
    if normalized.startswith(
        ("api:external", "external:", "scrape:", "crawler:", "firecrawl:", "llm:")
    ):
        return True
    if normalized.startswith("agent:") and any(
        marker in normalized
        for marker in ("external", "scrape", "crawler", "firecrawl", "llm")
    ):
        return True
    return False


def _has_taint_token(meta: Optional[dict[str, Any]]) -> bool:
    """Recognize explicit CORTEX taint/provenance tokens in metadata."""
    if not meta:
        return False
    for key in _TAINT_KEYS:
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return True
    custody = meta.get("event_source_key_custody")
    if isinstance(custody, dict):
        return any(
            isinstance(custody.get(key), str) and custody[key].strip()
            for key in ("custody_model", "assurance_level", "public_key_sha256")
        )
    return False


def _has_deterministic_validation(meta: Optional[dict[str, Any]]) -> bool:
    """Recognize explicit deterministic validation before high-confidence admission."""
    if not meta:
        return False

    direct_flags = (
        "deterministic_validation",
        "deterministic_validation_passed",
        "validated",
    )
    for key in direct_flags:
        value = meta.get(key)
        if value is True:
            return True
        if isinstance(value, str) and value.strip().casefold() in {
            "passed",
            "verified",
            "true",
            "valid",
        }:
            return True

    for key in ("validation", "verification", "validation_result"):
        value = meta.get(key)
        if isinstance(value, dict):
            status = value.get("status") or value.get("result")
            if isinstance(status, str) and status.strip().casefold() in {
                "passed",
                "verified",
                "valid",
            }:
                return True

    return False


class StoreProposal(BaseModel):
    """Rigid state collapse for CORTEX store operations."""

    model_config = ConfigDict(strict=False, extra="forbid")

    project: str = Field(min_length=1, max_length=_MAX_PROJECT_LENGTH)
    content: str = Field(min_length=_MIN_CONTENT_LENGTH, max_length=_MAX_CONTENT_LENGTH)
    fact_type: str = Field(default="knowledge")
    source: str = Field(min_length=1)
    confidence: str = Field(default="stated")
    tags: Optional[list[str]] = Field(default=None, max_length=_MAX_TAGS)
    meta: Optional[dict[str, Any]] = Field(default=None)

    @field_validator("project")
    @classmethod
    def validate_project(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("project cannot be empty")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        v = v.strip()
        if len(v) < _MIN_CONTENT_LENGTH:
            raise ValueError(f"content too short ({len(v)} chars, min {_MIN_CONTENT_LENGTH})")
        for pattern in _POISON_PATTERNS:
            if pattern.search(v):
                logger.warning(
                    "StoreProposal BLOCKED: poisoning pattern detected: %s", pattern.pattern
                )
                raise ValueError(
                    "content rejected: suspicious pattern detected (possible data poisoning / prompt injection)"
                )
        return v

    @field_validator("fact_type")
    @classmethod
    def validate_fact_type(cls, v: str) -> str:
        if v not in _ALLOWED_FACT_TYPES:
            raise ValueError(
                f"'{v}' not in allowed types: {', '.join(sorted(_ALLOWED_FACT_TYPES))}"
            )
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError(
                "source attribution is mandatory. Use 'cli', 'agent:<name>', 'api', or 'human' as source."
            )
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: str) -> str:
        if v not in _ALLOWED_CONFIDENCE:
            raise ValueError(
                f"'{v}' not in allowed confidence levels: {', '.join(sorted(_ALLOWED_CONFIDENCE))}"
            )
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v: Any) -> Any:
        # Defensive coercion: string tags → list (prevents corrupt JSON in DB)
        if isinstance(v, str):
            raise ValueError(
                f"tags must be list[str], got str: {v!r}. Use --tags with comma-separated values via CLI, or pass a list."
            )
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        for tag in v:
            if not isinstance(tag, str) or len(tag) > _MAX_TAG_LENGTH:
                raise ValueError(f"invalid tag: {tag!r}")
        return v


class StorageGuard:
    """Mandatory pre-store validation middleware.

    Every store() call in CORTEX passes through StorageGuard.validate()
    BEFORE the fact touches the database. Guards are non-bypassable:
    they run inside _store_impl, not in an optional wrapper.
    """

    @classmethod
    def validate(
        cls,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        source: Optional[str] = None,
        confidence: str = "stated",
        tags: Optional[list[str]] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> None:
        """Run ALL mandatory pre-store checks via Pydantic state collapse.

        Raises GuardViolation with the specific rule that was violated.
        """
        effective_source = source.strip() if isinstance(source, str) else ""
        try:
            StoreProposal(
                project=project,
                content=content,
                fact_type=fact_type,
                source=effective_source,
                confidence=confidence,
                tags=tags,
                meta=meta,
            )
        except ValidationError as e:
            # We map Pydantic validation errors back to GuardViolation semantics
            # to maintain backwards compatibility with the existing error catching
            # in tests and API endpoints.
            err = e.errors()[0]
            loc = ".".join(str(part) for part in err["loc"])
            msg = err["msg"]

            # Try to infer the old rule names based on loc
            if "project" in loc:
                if "empty" in msg or "at least 1" in msg:
                    raise GuardViolation("PROJECT_REQUIRED", "project cannot be empty") from e
                raise GuardViolation("PROJECT_TOO_LONG", msg.replace("Value error, ", "")) from e
            elif "content" in loc:
                if "empty" in msg or "at least 1" in msg:
                    raise GuardViolation("CONTENT_REQUIRED", "content cannot be empty") from e
                if "too short" in msg:
                    raise GuardViolation(
                        "CONTENT_TOO_SHORT", msg.replace("Value error, ", "")
                    ) from e
                if "poisoning" in msg:
                    raise GuardViolation(
                        "POISONING_DETECTED", msg.replace("Value error, ", "")
                    ) from e
                raise GuardViolation("CONTENT_TOO_LONG", msg.replace("Value error, ", "")) from e
            elif "fact_type" in loc:
                raise GuardViolation("INVALID_FACT_TYPE", msg.replace("Value error, ", "")) from e
            elif "source" in loc:
                raise GuardViolation("SOURCE_REQUIRED", msg.replace("Value error, ", "")) from e
            elif "confidence" in loc:
                raise GuardViolation("INVALID_CONFIDENCE", msg.replace("Value error, ", "")) from e
            elif "tags" in loc:
                if "str" in msg or "list" in msg:
                    raise GuardViolation("TAGS_TYPE_ERROR", msg.replace("Value error, ", "")) from e
                if "invalid tag" in msg:
                    raise GuardViolation("INVALID_TAG", msg.replace("Value error, ", "")) from e
                raise GuardViolation("TOO_MANY_TAGS", msg.replace("Value error, ", "")) from e

            # Fallback
            raise GuardViolation("VALIDATION_ERROR", f"{loc}: {msg}") from e

        source_requires_taint = _source_requires_taint(effective_source)
        if source_requires_taint:
            if not _has_taint_token(meta):
                raise GuardViolation(
                    "PROVENANCE_TAINT_REQUIRED",
                    "external or scraped sources require explicit CORTEX taint metadata",
                )
            if confidence in {"verified", "C5"} and not _has_deterministic_validation(meta):
                raise GuardViolation(
                    "DETERMINISTIC_VALIDATION_REQUIRED",
                    "external, scraped, or generative sources require deterministic "
                    "validation before high-confidence fact admission",
                )

        logger.debug(
            "StorageGuard PASS: project=%s, type=%s, source=%s, len=%d",
            project,
            fact_type,
            effective_source,
            len(content),
        )
