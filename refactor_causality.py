import os
import re
from pathlib import Path

def refactor_causality():
    # 1. Refactor causality.py (babylon60)
    filepath = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/babylon60/engine/causality.py")
    content = filepath.read_text(encoding="utf-8")
    
    content = content.replace(
        "def propagate_refutation(graph: CausalGraph, refuted_event_id: str, decay: float = 0.35) -> None:",
        "def propagate_refutation(graph: CausalGraph, refuted_event_id: str, decay_factor: Babylon60 | None = None) -> None:\n    if decay_factor is None:\n        decay_factor = Babylon60(75600)  # 0.35 * 216000"
    )
    content = content.replace(
        "            event.trust_score = 0.0",
        "            event.trust_score = Babylon60(0)"
    )
    # The complex line:
    content = content.replace(
        "            event.trust_score = max(0.0, event.trust_score * (1.0 - decay / max(depth, 1)))",
        "            depth_factor = Babylon60(max(depth, 1) * 216000)\n            retention = Babylon60(216000) - (decay_factor / depth_factor)\n            if retention.value < 0:\n                retention = Babylon60(0)\n            event.trust_score = event.trust_score * retention\n            if event.trust_score.value < 0:\n                event.trust_score = Babylon60(0)"
    )
    content = content.replace(
        "confidence: Babylon60 = Babylon60.from_float(1.0)",
        "confidence: Babylon60 = Babylon60(216000)"
    )
    content = content.replace(
        "confidence: Babylon60 = Babylon60.from_float(1.0) ,",
        "confidence: Babylon60 = Babylon60(216000),"
    )
    filepath.write_text(content, encoding="utf-8")
    
    # 2. Refactor causality_models.py (babylon60)
    filepath = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/babylon60/engine/causality_models.py")
    content = filepath.read_text(encoding="utf-8")
    
    content = content.replace("Babylon60.from_float(0.0001)", "Babylon60(22)")  # 0.0001 * 216000 = 21.6 -> 22
    content = content.replace("Babylon60.from_float(0.0)", "Babylon60(0)")
    
    content = content.replace(
        "delta_seconds = max(0.0, (curr_dt - last_dt).total_seconds())",
        "delta_seconds = max(0, int((curr_dt - last_dt).total_seconds()))"
    )
    content = content.replace(
        "return calculate_decay_weight(self.confidence_score, delta_seconds, self.decay_rate)",
        "return Babylon60(calculate_decay_weight(self.confidence_score.value, delta_seconds, 10000))"
    )
    filepath.write_text(content, encoding="utf-8")

if __name__ == "__main__":
    refactor_causality()
