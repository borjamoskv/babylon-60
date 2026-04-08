"""CORTEX Sovereign Niche Arbitrage Skill."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import MarketReport, NicheTarget, TrendSignal
    from .pipeline import NicheArbitrageEngine

__all__ = [
    "MarketReport",
    "NicheArbitrageEngine",
    "NicheTarget",
    "TrendSignal",
]


def __getattr__(name: str) -> object:
    """Lazily expose the public arbitrage symbols."""
    if name in {"MarketReport", "NicheTarget", "TrendSignal"}:
        from .models import MarketReport, NicheTarget, TrendSignal

        values = {
            "MarketReport": MarketReport,
            "NicheTarget": NicheTarget,
            "TrendSignal": TrendSignal,
        }
        return values[name]

    if name == "NicheArbitrageEngine":
        from .pipeline import NicheArbitrageEngine

        return NicheArbitrageEngine

    msg = f"module 'cortex.extensions.skills.niche_arbitrage' has no attribute {name!r}"
    raise AttributeError(msg)
