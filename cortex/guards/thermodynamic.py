from enum import Enum
from typing import Optional

class AgentMode(str, Enum):
    PLANNING = "PLANNING"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"
    DECORATIVE = "DECORATIVE"
    ACTIVE = "ACTIVE"

class ThermodynamicCounters:
    """Tracks exergy and thermodynamic metrics."""
    def __init__(self):
        self.total_exergy = 0.0
        self.total_waste = 0.0
        self.violations = 0

def should_enter_decorative_mode(exergy_score: float, threshold: float = 0.5) -> bool:
    """Returns True if the exergy score is low enough to trigger decorative mode (violation)."""
    return exergy_score < threshold
