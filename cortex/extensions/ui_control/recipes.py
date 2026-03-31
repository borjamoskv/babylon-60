"""
Recipe — Motor de "Recetas" JIT para Mac Maestro.
Almacena y reproduce secuencias deterministas de acciones UIAction.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("cortex.extensions.ui_control.recipes")

@dataclass
class RecipeStep:
    vector: str
    action: str
    target: Optional[dict[str, Any]] = None
    params: Optional[dict[str, Any]] = None

@dataclass
class Recipe:
    id: str
    trigger_phrase: str
    steps: list[RecipeStep]
    timestamp: str = datetime.now(timezone.utc).isoformat()
    confidence: float = 1.0

class RecipeManager:
    """Maneja la persistencia y carga de recetas JIT en ~/.cortex/recipes."""

    def __init__(self) -> None:
        self.base_dir = os.path.expanduser("~/.cortex/maestro/recipes")
        os.makedirs(self.base_dir, exist_ok=True)

    def save_recipe(self, recipe: Recipe) -> str:
        """Guarda una receta en un archivo JSON."""
        path = os.path.join(self.base_dir, f"{recipe.id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(recipe), f, indent=2, ensure_ascii=False)
        logger.info("Receta '%s' guardada en %s", recipe.id, path)
        return path

    def load_recipe(self, recipe_id: str) -> Optional[Recipe]:
        """Carga una receta por ID."""
        path = os.path.join(self.base_dir, f"{recipe_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            steps = [RecipeStep(**s) for s in data.pop("steps", [])]
            return Recipe(steps=steps, **data)

    def find_match(self, user_request: str) -> Optional[Recipe]:
        """Busca una receta que coincida con el prompt del usuario."""
        for filename in os.listdir(self.base_dir):
            if filename.endswith(".json"):
                recipe = self.load_recipe(filename[:-5])
                if recipe and recipe.trigger_phrase.lower() in user_request.lower():
                    return recipe
        return None
