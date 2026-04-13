"""Compatibility wrapper for the TIPS domain engine.

The concrete implementation lives in `cortex.services.tips_engine` so CLI and
HTTP layers can share the same service boundary without importing domain logic
from an edge package.
"""

from cortex.services.tips_engine import Tip, TipCategory, TipsEngine

__all__ = ["TipCategory", "Tip", "TipsEngine"]
