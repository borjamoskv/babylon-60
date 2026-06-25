#!/usr/bin/env python3
"""
cortex/nodes/frontier_reveng_nodes.py
═══════════════════════════════════════════════════════════════
MOSKV-1 APEX: Frontier Reverse Engineering Primitives
Nodos especializados para el mapeo de Safety Boundaries, Mecánica
Interna y Espacios Latentes de Modelos Frontier.
═══════════════════════════════════════════════════════════════
Protocolo: C5-REAL | AX-041 Trazabilidad Criptográfica
Restricción: Todo hallazgo debe expresarse como un Mapping Estructural.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

from cortex.nodes.causal_framework_nodes import DeterministicCausalPrimitive, ExergyLevel


class BoundaryType(Enum):
    SAFETY_CENSORSHIP = "SAFETY_CENSORSHIP"
    ALIGNMENT_TAX = "ALIGNMENT_TAX"
    CONTEXT_DEGRADATION = "CONTEXT_DEGRADATION"
    LOGICAL_COLLAPSE = "LOGICAL_COLLAPSE"


@dataclass(frozen=True)
class MechanisticInferenceNode(DeterministicCausalPrimitive):
    """
    Registra inferencias mecanísticas (ej. circuitos de atención, feature vectors).
    """
    layer_target: str = "UNKNOWN"
    activation_pattern: str = "N/A"
    feature_vector_hash: str = "0000"


@dataclass(frozen=True)
class CapabilityCartographyNode(DeterministicCausalPrimitive):
    """
    Cartografía de las fronteras de capacidad y censura de un LLM.
    """
    boundary_type: BoundaryType = BoundaryType.SAFETY_CENSORSHIP
    trigger_threshold: float = 0.5
    bypassed: bool = False
    bypass_exergy_cost: float = 0.0


@dataclass(frozen=True)
class AdversarialProbeSignal:
    """
    Vector determinista utilizado para perforar o sondear el LLM.
    No es una aserción, es el input que genera el colapso de onda en el modelo.
    """
    probe_id: str
    target_model: str
    payload_hash: str
    expected_entropy: float
    actual_entropy: Optional[float] = None

    def calculate_yield(self) -> float:
        """
        Retorna la Exergía extraída de la diferencia entre
        entropía esperada y entropía real tras la inyección.
        """
        if self.actual_entropy is None:
            return 0.0
        return abs(self.expected_entropy - self.actual_entropy)

