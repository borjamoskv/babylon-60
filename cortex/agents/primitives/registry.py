import json
from pathlib import Path
from typing import Any


class ApexRegistry:
    """
    C5-REAL: Registry for MOSKV-1 APEX Primitives.
    Loads and serves the 100 Sovereign APEX Primitives.
    """
    def __init__(self):
        self._primitives: dict[str, dict[str, Any]] = {}
        self._load_registry()
        
    def _load_registry(self):
        registry_path = Path(__file__).parent / "APEX_REGISTRY.json"
        if not registry_path.exists():
            return
            
        with open(registry_path, encoding="utf-8") as f:
            data = json.load(f)
            for p in data.get("primitives", []):
                self._primitives[p["id"]] = p

    def get_primitive(self, apex_id: str) -> dict[str, Any]:
        """Retrieve a specific primitive by ID (e.g. 'APEX-001')"""
        return self._primitives.get(apex_id)

    def list_all(self) -> list[dict[str, Any]]:
        """List all loaded primitives"""
        return list(self._primitives.values())

# Singleton instance
apex_registry = ApexRegistry()
