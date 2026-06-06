from typing import Optional, Dict, Any
from .state import RuntimeState

class SnapshotManager:
    """Freezes reality into compressed hashes every N causal steps."""
    
    def __init__(self, interval: int = 10):
        self.interval = interval
        # In memory for Sprint 0. Moving to Postgres/Disk in Sprint 1.
        self.snapshots: Dict[int, Dict[str, Any]] = {}

    def maybe_save(self, state: RuntimeState) -> Optional[str]:
        if state.version > 0 and state.version % self.interval == 0:
            self.snapshots[state.version] = {
                "version": state.version,
                "hash": state.hash,
                "data": dict(state.data)
            }
            return state.hash
        return None

    def load_latest(self) -> Optional[RuntimeState]:
        if not self.snapshots:
            return None
        latest_version = max(self.snapshots.keys())
        snap = self.snapshots[latest_version]
        return RuntimeState(initial_state=snap["data"], version=snap["version"])
