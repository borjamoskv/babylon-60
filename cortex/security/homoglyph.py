# [C5-REAL] Exergy-Maximized
"""
Homoglyph Guard (Ω_homoglyph): Defends against Unicode & mixed-script confusable attacks.
Particularly effective against BPE token masquerading (e.g., mixing Cyrillic/Greek/Latin).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Mapping
from typing import Any

from cortex.security.types import GuardViolation

logger = logging.getLogger("cortex.security.homoglyph")


class HomoglyphGuard:
    """Validates and enforces script isolation within individual words to block homoglyph injections."""

    @staticmethod
    def is_mixed_script(word: str) -> bool:
        """Detects if a single alphabetical word blends Latin, Cyrillic, or Greek scripts."""
        clean_word = "".join(c for c in word if c.isalpha())
        if not clean_word:
            return False

        scripts = set()
        for char in clean_word:
            try:
                name = unicodedata.name(char)
                script = name.split()[0]
                if script in {"LATIN", "CYRILLIC", "GREEK"}:
                    scripts.add(script)
            except ValueError:
                continue

        return len(scripts) > 1

    @staticmethod
    def validate(content: str) -> bool:
        """Validates that no word in the content utilizes mixed-script confusables."""
        if not content:
            return True

        # Split content into words by whitespace and common punctuation delimiters
        words = re.split(r"[\s\n\r\t.,;:!?()\"'\[\]{}<>]+", content)
        for word in words:
            if not word:
                continue
            if HomoglyphGuard.is_mixed_script(word):
                logger.warning("Homoglyph detected in word: %r", word)
                return False
        return True

    @staticmethod
    def enforce(content: str, metadata: Mapping[str, Any] | None = None) -> None:
        """Enforces that input content does not contain homoglyph/mixed-script bypasses."""
        if not HomoglyphGuard.validate(content):
            raise GuardViolation("Input rejected: Homoglyph/Mixed-script bypass attempt detected.")
