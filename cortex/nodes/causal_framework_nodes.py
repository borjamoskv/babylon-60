#!/usr/bin/env python3
"""
cortex/nodes/causal_framework_nodes.py
═══════════════════════════════════════════════════════════════
MOSKV-1 APEX: Deterministic Causal Primitive Framework
Cristalización de Primitivas Causales para CORTEX-Persist.
Migración LEY 11 (BABYLON-60 Epistemology): Erradicación de float64.
═══════════════════════════════════════════════════════════════
"""

import os
import sys
from dataclasses import dataclass
from enum import Enum

# Asegurar que importamos cortex_core_rs.py desde el root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
try:
    from cortex_core_rs import Babylon60
except ImportError:
    class Babylon60:
        pass # Fallback no utilizado

class ExergyLevel(Enum):
    ZERO_YIELD = "ZERO_YIELD"
    C4_SIM = "C4_SIM"
    C5_REAL = "C5_REAL"


@dataclass(frozen=True)
class DeterministicCausalPrimitive:
    """
    Representa una transformación física o matemática determinista.
    Mapeo isomorfo: [Input State] -> [Operation] -> [Output State]
    Utiliza Babylon60 nativo para evitar entropía estocástica (float errors).
    """
    primitive_id: str
    name: str
    input_state: str
    operation: str
    output_state: str
    exergy_level: ExergyLevel = ExergyLevel.C5_REAL
    cost_complexity: Babylon60 = None
    empirical_accuracy: Babylon60 = None

    def compute_friston_penalty(self) -> Babylon60:
        """AUTO-8: Penalización de Energía Libre Variacional."""
        # Friston penalty deduction: Complexity / (Accuracy + 1) * 0.05
        # BABYLON-60 Integer Math
        acc_plus_one = self.empirical_accuracy + Babylon60.from_int(1)
        # Factor = 0.05 (1/20 -> 0.05 en Babylon60)
        factor = Babylon60.from_float(0.05)
        
        # penalty = (cost_complexity / acc_plus_one) * factor
        # En Babylon60 (cost / acc) devuelve Babylon60 escalado
        division = self.cost_complexity / acc_plus_one
        penalty = division * factor
        return penalty

    def validate_exergy(self, base_exergy: Babylon60) -> bool:
        """Net exergy must be >= 0.1 to permit DB writes (AUTO-8)."""
        net_exergy = base_exergy - self.compute_friston_penalty()
        threshold = Babylon60.from_float(0.1)
        return net_exergy >= threshold


@dataclass(frozen=True)
class IsomorphicMapping:
    source_primitive_id: str
    target_primitive_id: str
    mapping_function: str
    is_reversible: bool = True


class FristonPenaltyValidator:
    """Validador centralizado para inyección causal (BABYLON-60 Native)."""
    
    @staticmethod
    def validate(primitive: DeterministicCausalPrimitive, base_exergy: Babylon60) -> bool:
        if not primitive.validate_exergy(base_exergy):
            raise ValueError(f"Rechazo Físico: {primitive.primitive_id} excede el Límite de Penalización de Friston. (Exergía neta < 0.1 en BABYLON-60)")
        return True
