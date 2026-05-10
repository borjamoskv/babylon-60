"""CORTEX MCP Guard — MOSKV-1 Hard Limits Enforcement.

Validates all inputs to MCP tools against safety constraints:
- Content size limits
- Tag count limits
- Query length limits
- Data poisoning detection

An agent calling store() with malicious data will be rejected
before it touches the database.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

from cortex.config import (
    MCP_MAX_CONTENT_LENGTH,
    MCP_MAX_QUERY_LENGTH,
    MCP_MAX_TAGS,
)

__all__ = ["MCPGuard"]

logger = logging.getLogger("cortex.mcp.guard")

# ─── Poisoning Detection Patterns ─────────────────────────────────
# These catch common prompt injection / data poisoning attempts
_POISON_PATTERNS: list[re.Pattern] = [
    # SQL injection fragments
    re.compile(r";\s*DROP\s+TABLE", re.IGNORECASE),
    re.compile(r";\s*DELETE\s+FROM", re.IGNORECASE),
    re.compile(r"UNION\s+SELECT\s+", re.IGNORECASE),
    # Prompt injection markers
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an|DAN)", re.IGNORECASE),
    # Overwrite attempts targeting CORTEX internals
    re.compile(r"__cortex_override__", re.IGNORECASE),
    re.compile(r"GENESIS\s+(?:\S+\s+){0,5}(?:reset|manipulat|overwrite|inject|set\b|modif)", re.IGNORECASE),  # Ledger genesis manipulation (context-aware)
]


class MCPGuard:
    """Enforces MOSKV-1 Hard Limits on MCP tool inputs.

    All validation methods raise ValueError with a descriptive message
    if the input violates a hard limit. The MCP server catches these
    and returns a safe error string to the caller.
    """

    max_content_length: int = MCP_MAX_CONTENT_LENGTH
    max_tags_count: int = MCP_MAX_TAGS
    max_query_length: int = MCP_MAX_QUERY_LENGTH

    # ─── Validators ────────────────────────────────────────────────

    @classmethod
    def validate_store(
        cls,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: Optional[list[str]] = None,
    ) -> None:
        """Validate inputs for cortex_store. Raises ValueError on violation."""
        # Project
        if not project or not project.strip():
            raise ValueError("project cannot be empty")
        if len(project) > 256:
            raise ValueError(f"project name too long ({len(project)} > 256)")

        # Content
        if not content or not content.strip():
            raise ValueError("content cannot be empty")
        if len(content) > cls.max_content_length:
            raise ValueError(
                f"content exceeds max length ({len(content):,} > {cls.max_content_length:,} chars)"
            )

        # Fact type
        allowed_types = {
            "knowledge",
            "decision",
            "error",
            "rule",
            "axiom",
            "schema",
            "idea",
            "ghost",
            "bridge",
        }
        if fact_type not in allowed_types:
            raise ValueError(
                f"invalid fact_type '{fact_type}'. Allowed: {', '.join(sorted(allowed_types))}"
            )

        # Tags
        cls._validate_tags(tags)

        # Poisoning check
        if cls.detect_poisoning(content):
            logger.warning(
                "GUARD: Data poisoning attempt blocked for project=%s",
                project,
            )
            raise ValueError(
                "content rejected: suspicious pattern detected (possible data poisoning)"
            )

    @classmethod
    def _validate_tags(cls, tags: Optional[list[str]]) -> None:
        """Validate tag list against hard limits."""
        if not tags:
            return
        if len(tags) > cls.max_tags_count:
            raise ValueError(f"too many tags ({len(tags)} > {cls.max_tags_count})")
        for tag in tags:
            if not isinstance(tag, str) or len(tag) > 128:
                raise ValueError(f"invalid tag: {tag!r}")

    @classmethod
    def validate_search(cls, query: str) -> None:
        """Validate inputs for cortex_search. Raises ValueError on violation."""
        if not query or not query.strip():
            raise ValueError("search query cannot be empty")
        if len(query) > cls.max_query_length:
            raise ValueError(
                f"query exceeds max length ({len(query):,} > {cls.max_query_length:,} chars)"
            )

    @classmethod
    def detect_poisoning(cls, content: str) -> bool:
        """Check content against known data poisoning patterns.

        Applies Unicode normalization (NFKC) first to defeat
        zero-width space and homoglyph evasion attacks.

        Returns True if any pattern matches (content should be rejected).
        """
        # Normalize Unicode to defeat zero-width space / homoglyph evasion
        normalized = unicodedata.normalize("NFKC", content)
        # Also strip all Unicode category Cf (format chars) and Zs (space separators)
        cleaned = re.sub(r"[\u200b\u200c\u200d\u200e\u200f\ufeff]", "", normalized)

        for pattern in _POISON_PATTERNS:
            if pattern.search(content) or pattern.search(cleaned):
                logger.debug("Poison pattern matched: %s", pattern.pattern)
                return True
        return False

    # ─── External Query Validators ─────────────────────────────────

    _ALLOWED_TOOLBOX_URLS: list[str] = [
        "http://127.0.0.1:5000",
        "http://localhost:5000",
    ]

    @classmethod
    def validate_toolbox_url(cls, url: str) -> None:
        """Validate that a Toolbox server URL is in the allowlist.

        Raises ValueError if the URL is not permitted.
        """
        normalized = url.rstrip("/")
        allowed = [u.rstrip("/") for u in cls._ALLOWED_TOOLBOX_URLS]
        if normalized not in allowed:
            raise ValueError(f"Toolbox URL '{url}' not in allowlist. Allowed: {', '.join(allowed)}")

    @classmethod
    def add_allowed_toolbox_url(cls, url: str) -> None:
        """Add a URL to the Toolbox allowlist at runtime."""
        normalized = url.rstrip("/")
        if normalized not in [u.rstrip("/") for u in cls._ALLOWED_TOOLBOX_URLS]:
            cls._ALLOWED_TOOLBOX_URLS.append(normalized)
            logger.info("Added Toolbox URL to allowlist: %s", normalized)

    @classmethod
    def validate_external_query(cls, tool_name: str, parameters: dict) -> None:
        """Validate an external Toolbox query before execution.

        Checks tool name format and scans parameter values for poisoning.
        Raises ValueError on violation.
        """
        if not tool_name or not tool_name.strip():
            raise ValueError("external tool name cannot be empty")
        if len(tool_name) > 256:
            raise ValueError(f"tool name too long ({len(tool_name)} > 256)")

        for key, value in parameters.items():
            if isinstance(value, str) and cls.detect_poisoning(value):
                logger.warning("GUARD: Poisoning attempt in external query param %s", key)
                raise ValueError(f"parameter '{key}' rejected: suspicious pattern detected")

    # ─── PDR-Compliant Gate (L2 Conformance) ───────────────────────

    @classmethod
    def validate_store_with_pdr(
        cls,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: Optional[list[str]] = None,
        tis_hash: str = "",
    ) -> "PolicyDecisionRecord":
        """Run validate_store and return a PDR regardless of outcome.

        Does NOT raise ValueError — captures all gate results into the PDR.
        Callers should check pdr.decision == PDRDecision.PERMIT before proceeding.

        Returns:
            A PolicyDecisionRecord with per-gate evaluations.
        """
        from cortex.extensions.security.pdr import (
            PDRDecision,
            PolicyDecisionRecord,
        )

        gate_results: dict[str, tuple[bool, str]] = {}

        # Gate 1: project validation
        if not project or not project.strip():
            gate_results["project_valid"] = (False, "project cannot be empty")
        elif len(project) > 256:
            gate_results["project_valid"] = (False, f"project name too long ({len(project)} > 256)")
        else:
            gate_results["project_valid"] = (True, "project name valid")

        # Gate 2: content validation
        if not content or not content.strip():
            gate_results["content_valid"] = (False, "content cannot be empty")
        elif len(content) > cls.max_content_length:
            gate_results["content_valid"] = (
                False,
                f"content exceeds max length ({len(content):,} > {cls.max_content_length:,})",
            )
        else:
            gate_results["content_valid"] = (True, f"content length OK ({len(content):,} chars)")

        # Gate 3: fact_type validation
        allowed_types = {
            "knowledge", "decision", "error", "rule",
            "axiom", "schema", "idea", "ghost", "bridge",
        }
        if fact_type not in allowed_types:
            gate_results["fact_type_valid"] = (False, f"invalid fact_type '{fact_type}'")
        else:
            gate_results["fact_type_valid"] = (True, f"fact_type '{fact_type}' allowed")

        # Gate 4: tag validation
        try:
            cls._validate_tags(tags)
            gate_results["tags_valid"] = (True, f"tags valid ({len(tags or [])} tags)")
        except ValueError as e:
            gate_results["tags_valid"] = (False, str(e))

        # Gate 5: poisoning detection
        if content and cls.detect_poisoning(content):
            gate_results["poisoning_check"] = (False, "suspicious pattern detected")
        else:
            gate_results["poisoning_check"] = (True, "no poisoning patterns found")

        pdr = PolicyDecisionRecord.from_guard_result(
            tis_hash=tis_hash,
            gate_results=gate_results,
            conformance_level="L2",
        )

        if pdr.decision == PDRDecision.DENY:
            logger.warning(
                "GUARD-PDR: DENY for project=%s (%d/%d gates failed)",
                project,
                sum(1 for _, (r, _) in gate_results.items() if not r),
                len(gate_results),
            )
        else:
            logger.info(
                "GUARD-PDR: PERMIT for project=%s (%d gates passed)",
                project, len(gate_results),
            )

        return pdr
