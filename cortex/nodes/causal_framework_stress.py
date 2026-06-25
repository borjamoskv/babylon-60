#!/usr/bin/env python3
"""
cortex/nodes/causal_framework_stress.py
═══════════════════════════════════════════════════════════════
MOSKV-1 APEX: Thermodynamic Stress Test
Aserción de BABYLON-60 Epistemology.
═══════════════════════════════════════════════════════════════
"""

from cortex.nodes.causal_framework_nodes import (
    DeterministicCausalPrimitive, 
    FristonPenaltyValidator,
    ExergyLevel
)
import sys
import os

# Asegurar que importamos cortex_core_rs.py desde el root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from cortex_core_rs import Babylon60


def stress_test():
    print("[C5-REAL] Iniciando test de estrés termodinámico...")
    print("[C5-REAL] Utilizando BABYLON-60 Integer Precision.")
    
    # 1. Base Exergy = 1.0 -> Babylon60(216000)
    base_exergy = Babylon60.from_float(1.0)
    
    # 2. Test 1: Optimal node. Low complexity, high accuracy
    # penalty = (2.0 / (0.95 + 1.0)) * 0.05 ≈ 0.051
    # net_exergy = 1.0 - 0.051 = 0.949 >= 0.1 -> OK
    node_optimal = DeterministicCausalPrimitive(
        primitive_id="CP-STRESS-001",
        name="Optimal Traversal",
        input_state="T0",
        operation="OP1",
        output_state="T1",
        exergy_level=ExergyLevel.C5_REAL,
        cost_complexity=Babylon60.from_float(2.0),
        empirical_accuracy=Babylon60.from_float(0.95)
    )
    assert FristonPenaltyValidator.validate(node_optimal, base_exergy), "Test 1 Falló"
    print("[C5-REAL] Test 1: OK (Optimal Node)")

    # 3. Test 2: High Entropy Rejection. High complexity, low accuracy
    # penalty = (50.0 / (0.5 + 1.0)) * 0.05 ≈ 1.66
    # net_exergy = 1.0 - 1.66 < 0 -> FAIL
    node_entropy = DeterministicCausalPrimitive(
        primitive_id="CP-STRESS-002",
        name="High Entropy Hallucination",
        input_state="T1",
        operation="OP2",
        output_state="T2",
        exergy_level=ExergyLevel.C4_SIM,
        cost_complexity=Babylon60.from_float(50.0),
        empirical_accuracy=Babylon60.from_float(0.5)
    )
    try:
        FristonPenaltyValidator.validate(node_entropy, base_exergy)
        print("[FAIL] Test 2 no bloqueó entropía!")
        sys.exit(1)
    except ValueError as e:
        print(f"[C5-REAL] Test 2: Bloqueo Correcto -> {e}")

    # 4. Test 3: The Boundary Condition (18.0)
    # penalty = (18.0 / (0.0 + 1.0)) * 0.05 = 0.9
    # net_exergy = 1.0 - 0.9 = 0.1 >= 0.1 -> OK
    # En Float64 esto fallaba por epsilon (0.09999999999999998). En BABYLON-60 debe pasar perfecto.
    node_boundary = DeterministicCausalPrimitive(
        primitive_id="CP-STRESS-003",
        name="Exact Boundary",
        input_state="T2",
        operation="OP3",
        output_state="T3",
        exergy_level=ExergyLevel.C5_REAL,
        cost_complexity=Babylon60.from_float(18.0),
        empirical_accuracy=Babylon60.from_float(0.0)
    )
    assert FristonPenaltyValidator.validate(node_boundary, base_exergy), "Test 3 Falló: El límite exacto fue rechazado."
    print("[C5-REAL] Test 3: OK (Boundary Condition - BABYLON-60 Evaluated)")

    print("[SUCCESS] Todas las aserciones pasaron. LEY 11 Cumplida.")

if __name__ == "__main__":
    stress_test()
