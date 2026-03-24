from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("cortex.swarm.guards.privacy_gate")


class PrivacyGate:
    """
    Sovereign Data Sanitizer (Ω-Architecture).

    Prevents PII (Personally Identifiable Information) and sensitive
    infrastructure data from leaking into external Cloud APIs (OpenAI, Claude).
    """

    def __init__(self, patterns: dict[str, str] | None = None) -> None:
        self.patterns = patterns or {
            "ipv4": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "aws_key": r"AKIA[0-9A-Z]{16}",
            "generic_token": r"(?i)(key|token|password|secret)[\s:=]+['\"]?([a-zA-Z0-9\-_]{20,})['\"]?",
        }
        self.compiled_rules = {name: re.compile(rule) for name, rule in self.patterns.items()}

    def sanitize(self, content: str) -> str:
        """Replace sensitive patterns with placeholders."""
        sanitized = content
        for label, regex in self.compiled_rules.items():
            matches = regex.findall(sanitized)
            if matches:
                logger.warning("PrivacyGate: Masking %d occurrences of %s", len(matches), label)
                sanitized = regex.sub(f"[MASKED_{label.upper()}]", sanitized)
        return sanitized

    def validate_outgoing(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        """Sanitize both task prompt and context values."""
        return {
            "task": self.sanitize(task),
            "context": {
                k: self.sanitize(str(v)) if isinstance(v, (str, bytes)) else v
                for k, v in context.items()
            },
        }
