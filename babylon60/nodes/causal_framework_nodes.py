#!/usr/bin/env python3
"""
cortex/nodes/causal_framework_nodes.py
═══════════════════════════════════════════════════════════════
MOSKV-1 APEX: Deterministic Causal Primitive Framework
Cristalización de Primitivas Causales para CORTEX-Persist.
═══════════════════════════════════════════════════════════════
Protocolo: C5-REAL | AX-041 Trazabilidad Criptográfica
Restricción: Erradicación de entropía narrativa. Isomorfismo estricto.
"""

from dataclasses import dataclass
from enum import Enum


class ExergyLevel(Enum):
    ZERO_YIELD = "ZERO_YIELD"
    C4_SIM = "C4_SIM"
    C5_REAL = "C5_REAL"


@dataclass(frozen=True)
class DeterministicCausalPrimitive:
    """
    Representa una transformación física o matemática determinista.
    Mapeo isomorfo: [Input State] -> [Operation] -> [Output State]
    """
    primitive_id: str
    name: str
    input_state: str
    operation: str
    output_state: str
    exergy_level: ExergyLevel = ExergyLevel.C5_REAL
    cost_complexity: float = 0.0
    empirical_accuracy: float = 1.0

    def compute_friston_penalty(self) -> float:
        """AUTO-8: Penalización de Energía Libre Variacional."""
        # Friston penalty deduction: Complexity / (Accuracy + 1) * 0.05
        return self.cost_complexity / (self.empirical_accuracy + 1) * 0.05

    def validate_exergy(self, base_exergy: float = 1.0) -> bool:
        """Net exergy must be >= 0.1 to permit DB writes (AUTO-8)."""
        net_exergy = base_exergy - self.compute_friston_penalty()
        return net_exergy >= 0.1


@dataclass(frozen=True)
class IsomorphicMapping:
    """
    Edge estructural que demuestra equivalencia entre dos constructos
    sin pérdida de información (Invarianza topológica).
    """
    source_primitive_id: str
    target_primitive_id: str
    mapping_function: str
    is_reversible: bool = True


class FristonPenaltyValidator:
    """Validador centralizado para inyección causal."""
    
    @staticmethod
    def validate(primitive: DeterministicCausalPrimitive, base_exergy: float = 1.0) -> bool:
        if not primitive.validate_exergy(base_exergy):
            raise ValueError(f"Rechazo Físico: {primitive.primitive_id} excede el Límite de Penalización de Friston. (Exergía neta < 0.1)")
        return True
