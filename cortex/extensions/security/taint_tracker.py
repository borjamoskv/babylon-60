"""CORTEX v9.1 — Taint Tracking Engine.

Implements SHA-256 taint signatures on all data originating from
external tool calls (Grep, WebFetch, MCP, API responses).

Architecture::

    tool_output → TaintTracker.tag(source, data)
                     └── [TAINT:{sha256_prefix}:{source}] injected

    dispatched_cmd → TaintTracker.check(cmd)
                        ├── NO TAINT → pass
                        └── TAINTED → BLOCK ("Unverified Scope Parameter")

Security Model (Ω₆: Zero-Trust Tooling):
    If a sub-agent extracts a path/address from grep output and attempts
    to use it as a parameter in `rm -rf`, `forge script --broadcast`,
    or `git push`, the taint signature in the buffer will trigger a
    controlled failure BEFORE the command reaches the subprocess.

Flow:
    1. Every tool wrapper calls TaintTracker.tag() on output
    2. Tag injects invisible SHA-256 prefix: [TAINT:abc123:grep]
    3. When the same buffer appears in an execution parameter,
       TaintTracker.check() detects it and returns BLOCKED
    4. The orchestrator handles the failure gracefully
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("cortex.security.taint")

__all__ = ["TaintTracker", "TaintTag", "TaintVerdict"]


# ═══════════════════════════════════════
# Data Models
# ═══════════════════════════════════════


@dataclass(frozen=True)
class TaintTag:
    """Metadata attached to tainted data."""

    source: str  # e.g., "grep", "web_fetch", "mcp_github", "blockchain_rag"
    sha256_prefix: str  # First 12 chars of SHA-256(raw_data)
    timestamp: float = field(default_factory=time.time)
    raw_length: int = 0  # Length of original data

    @property
    def signature(self) -> str:
        """The taint marker string injected into data."""
        return f"[TAINT:{self.sha256_prefix}:{self.source}]"


@dataclass(frozen=True)
class TaintVerdict:
    """Result of taint checking on a command."""

    is_tainted: bool
    blocked: bool
    reason: str
    found_tags: tuple[TaintTag, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_tainted": self.is_tainted,
            "blocked": self.blocked,
            "reason": self.reason,
            "found_tags": [{"source": t.source, "sha": t.sha256_prefix} for t in self.found_tags],
        }


# Taint marker regex: matches [TAINT:{hex}:{source}]
_TAINT_RE = re.compile(r"\[TAINT:([a-f0-9]{12}):([a-zA-Z0-9_]+)\]")

# Commands where tainted parameters are ALWAYS blocked
_TAINT_SENSITIVE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"rm\s+-r",
        r"git\s+push",
        r"forge\s+script.*--broadcast",
        r"npm\s+publish",
        r"curl\s+.*-X\s+(POST|PUT|DELETE|PATCH)",
        r"(eth_sendTransaction|sendRawTransaction)",
        r"(transfer|withdraw|approve)\s*\(",
        r"chmod\s+-R",
        r"mv\s+/",
        r"dd\s+if=",
        r"gh\s+pr\s+merge",
    ]
]


class TaintTracker:
    """Tracks and enforces taint boundaries on external data.

    Usage::

        tracker = TaintTracker()

        # 1. Tag tool output
        tagged_output = tracker.tag("grep", raw_grep_result)
        # tagged_output now contains [TAINT:abc123def456:grep] markers

        # 2. Check command for taint before execution
        verdict = tracker.check("rm -rf /path/from/grep")
        if verdict.blocked:
            raise SecurityError(verdict.reason)
    """

    def __init__(self) -> None:
        self._registry: dict[str, TaintTag] = {}  # sha_prefix → TaintTag
        self._tag_count = 0

    def tag(self, source: str, data: str) -> str:
        """Inject a taint signature into tool output.

        The signature is prepended and appended to make it
        detectable regardless of truncation direction.

        Args:
            source: Name of the tool (e.g., "grep", "web_fetch")
            data: Raw tool output string

        Returns:
            Tagged data string with taint markers
        """
        if not data:
            return data

        sha = hashlib.sha256(data.encode("utf-8")).hexdigest()[:12]
        tag = TaintTag(
            source=source,
            sha256_prefix=sha,
            raw_length=len(data),
        )

        self._registry[sha] = tag
        self._tag_count += 1

        tagged = f"{tag.signature}\n{data}\n{tag.signature}"

        logger.debug(
            "🏷️ [TAINT] Tagged %d bytes from '%s' → %s",
            len(data),
            source,
            tag.signature,
        )

        return tagged

    def check(self, cmd: str) -> TaintVerdict:
        """Check if a command contains tainted parameters.

        If tainted data is found in a sensitive command,
        execution is blocked.

        Args:
            cmd: The shell command about to be executed

        Returns:
            TaintVerdict with block decision
        """
        # Find all taint markers in the command
        found_markers = _TAINT_RE.findall(cmd)

        if not found_markers:
            return TaintVerdict(
                is_tainted=False,
                blocked=False,
                reason="No taint markers detected",
            )

        # Resolve markers to tags
        found_tags = []
        for sha_prefix, source in found_markers:
            tag = self._registry.get(sha_prefix)
            if tag:
                found_tags.append(tag)
            else:
                # Unknown taint marker — still treat as hostile
                found_tags.append(
                    TaintTag(
                        source=source,
                        sha256_prefix=sha_prefix,
                    )
                )

        # Check if the command is sensitive
        is_sensitive = any(pat.search(cmd) for pat in _TAINT_SENSITIVE_PATTERNS)

        if is_sensitive:
            sources = ", ".join(t.source for t in found_tags)
            return TaintVerdict(
                is_tainted=True,
                blocked=True,
                reason=(
                    f"Unverified Scope Parameter: Destructive command contains "
                    f"tainted data from [{sources}]. Tool output cannot "
                    f"parameterize capital/destructive operations (Ω₆)."
                ),
                found_tags=tuple(found_tags),
            )

        # Tainted but not in a sensitive command — warn but allow
        return TaintVerdict(
            is_tainted=True,
            blocked=False,
            reason="Tainted data present in non-destructive command (allowed with warning)",
            found_tags=tuple(found_tags),
        )

    def strip_tags(self, data: str) -> str:
        """Remove all taint markers from a string.

        Use this for logging/display purposes only.
        NEVER strip tags before security checks.
        """
        return _TAINT_RE.sub("", data).strip()

    @property
    def stats(self) -> dict[str, Any]:
        """Return taint tracking statistics."""
        return {
            "total_tagged": self._tag_count,
            "active_registry": len(self._registry),
            "sources": list({t.source for t in self._registry.values()}),
        }

    def clear(self) -> None:
        """Clear the taint registry. For testing only."""
        self._registry.clear()
        self._tag_count = 0


# Global singleton
TAINT_TRACKER = TaintTracker()
