# [C5-REAL] Exergy-Maximized
"""Shannon entropy calculation utility."""

from __future__ import annotations

import math


def shannon_entropy(content: str) -> float:
    """Calculate Shannon entropy of content."""
    if not content:
        return 0.0
    freq: dict[str, int] = {}
    for ch in content:
        freq[ch] = freq.get(ch, 0) + 1
    length = len(content)
    return -sum((c / length) * math.log2(c / length) for c in freq.values() if c > 0)
