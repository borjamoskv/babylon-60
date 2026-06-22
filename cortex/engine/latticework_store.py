# [C5-REAL] Exergy-Maximized
import logging
import os
import re
from typing import Optional
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

class CognitivePrimitive(BaseModel):
    id: int
    name: str
    algebraic_topology: str
    description: str
    base60_constant: int = 0

class LatticeworkStore:
    """
    [C5-REAL] O(1) in-memory epistemic foundation for the 100 Primitives of Cognitive Exergy.
    Serves as the truth-source for the LatticeworkDaemon's thermodynamic interventions.
    """
    def __init__(self):
        self.primitives: dict[int, CognitivePrimitive] = {}
        self._initialize_core_primitives()

    def _initialize_core_primitives(self):
        # Localizamos el archivo de mapeo estructural (C5-REAL Bridge)
        # Asume que se corre desde la raíz del proyecto o subimos un nivel si es necesario
        root_path = Path(__file__).parent.parent.parent
        mapping_path = root_path / "AUTODIDACT_SYSTEMS_EXERGY_MAPPING.md"
        
        if not mapping_path.exists():
            mapping_path = Path(os.getcwd()) / "AUTODIDACT_SYSTEMS_EXERGY_MAPPING.md"
            if not mapping_path.exists():
                logger.warning(f"[LatticeworkStore] No se encontró el manifiesto de exergía en {mapping_path}")
                return

        with open(mapping_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Regex para parsear cada primitiva desde el documento estructurado.
        pattern = re.compile(
            r"### (\d+)\.\s*(.*?)\n"
            r".*?\*\*Topología Algebraica:\*\*\s*`([^`]+)`\n"
            r".*?\*\*Isomorfismo Causal:\*\*\s*(.*?)\n"
            r"(?=(?:### \d+\.)|\Z)", 
            re.DOTALL | re.IGNORECASE
        )

        matches = pattern.findall(content)
        for match in matches:
            pid = int(match[0].strip())
            name = match[1].strip()
            algebra = match[2].strip()
            desc = match[3].strip()

            # Hash simple de la topología algebraica para extraer una constante Base-60
            b60_const = abs(hash(algebra)) % 3600

            self.primitives[pid] = CognitivePrimitive(
                id=pid, 
                name=name, 
                algebraic_topology=algebra, 
                description=desc,
                base60_constant=b60_const
            )
            
        logger.info(f"[LatticeworkStore] Cristalizadas {len(self.primitives)} primitivas topológicas en RAM (C5-REAL).")

    def get_primitive(self, pid: int) -> Optional[CognitivePrimitive]:
        return self.primitives.get(pid)

    def search_by_keyword(self, text: str) -> list[CognitivePrimitive]:
        text_lower = text.lower()
        return [
            p for p in self.primitives.values()
            if text_lower in p.name.lower() or text_lower in p.description.lower()
        ]
