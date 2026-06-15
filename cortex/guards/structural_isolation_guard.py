# [C5-REAL] Exergy-Maximized
"""CORTEX Structural Isolation Guard.

Enforces:
1. Reality level declaration (C5-REAL or C4-SIM)
2. No simulated proof in C5-REAL mode
3. Protected paths boundaries (Rule R5)
4. Link formatting rules (no backticks in Markdown links)

Reality Level: C5-REAL
"""

from __future__ import annotations

import logging
import re
from cortex.utils.errors import CortexError

logger = logging.getLogger("cortex.guards.structural_isolation_guard")


class StructuralIsolationViolation(ValueError, CortexError):
    """Exception raised when an artifact or content violates structural isolation guidelines."""


class StructuralIsolationGuard:
    """Enforces strict isolation rules for C5-REAL/C4-SIM outputs and markdown formatting."""

    PROTECTED_PATHS = [
        "/System/Volumes/Data/System/Library/AssetsV2",
        "/System/Volumes/Data/private/var/db/",
        "~/Library/Mobile Documents",
        "~/Library/Application Support/CloudDocs",
    ]

    # Detect links with backticks around the text, e.g. [`name`](url)
    BAD_LINK_PATTERN = re.compile(
        r"\[\`[^\`\]]+\`\]\((?:file|http|https|mailto):[^\)]+\)", re.IGNORECASE
    )

    def check(self, content: str) -> None:
        """Validates structural constraints on the provided content.

        Args:
            content: The text content to validate.

        Raises:
            StructuralIsolationViolation: If any structural constraint is violated.
        """
        if not content:
            return

        # 1. Reality Level Check
        has_c5 = "C5-REAL" in content
        has_c4 = "C4-SIM" in content

        if not has_c5 and not has_c4:
            raise StructuralIsolationViolation(
                "Missing reality level declaration. Content must declare 'C5-REAL' or 'C4-SIM'."
            )

        # 2. Simulation Integrity Check (C5-REAL cannot contain simulated claims)
        if has_c5:
            # Check for simulated keywords when claiming real execution
            sim_keywords = [
                "simulated capital",
                "simulated transaction",
                "simulated yield",
                "simulated proof",
                "simulation proof",
            ]
            for kw in sim_keywords:
                if kw in content.lower():
                    raise StructuralIsolationViolation(
                        f"Contradictory state: declared 'C5-REAL' but contains simulated proof keyword: '{kw}'."
                    )
            # If it declares C5-REAL, it shouldn't also declare C4-SIM
            if has_c4:
                raise StructuralIsolationViolation(
                    "Contradictory state: declared both 'C5-REAL' and 'C4-SIM'."
                )

        # 3. Protected Paths Check (R5 Protection)
        for path in self.PROTECTED_PATHS:
            if path in content:
                raise StructuralIsolationViolation(
                    f"Attempted access to protected path: '{path}'."
                )

        # 4. Markdown Link Formatting Check
        if self.BAD_LINK_PATTERN.search(content):
            raise StructuralIsolationViolation(
                "Markdown links must not surround link text with backticks (e.g., use [file](file://...) instead of [`file`](file://...))."
            )
