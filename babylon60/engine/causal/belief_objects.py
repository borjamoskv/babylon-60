from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class BeliefObject:
    """Stub de BeliefObject para persistencia en el enjambre. C5-REAL."""
    id: str
    phase: str
    data: Dict[str, Any] = field(default_factory=dict)
