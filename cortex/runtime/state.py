import hashlib
import json
from typing import Any, Dict

class RuntimeState:
    """Immutable causal state derived exclusively from the event ledger."""
    
    def __init__(self, initial_state: Dict[str, Any] = None, version: int = 0):
        self.data = initial_state or {}
        self.version = version
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        state_str = json.dumps(self.data, sort_keys=True)
        return hashlib.sha256(f"{self.version}:{state_str}".encode()).hexdigest()

    def apply_event(self, event: Dict[str, Any]) -> "RuntimeState":
        """Deterministic state evolution."""
        action = event.get("action_type")
        payload = event.get("payload", {})
        
        if action == "MEMORY_WRITE":
            self.data.update(payload)
        
        self.version += 1
        self.hash = self._compute_hash()
        return self
