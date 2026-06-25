#!/usr/bin/env python3
"""
babylon60/nodes/causal_framework_stress.py
═══════════════════════════════════════════════════════════════
MOSKV-1 APEX: Prueba de Estrés Termodinámico (AUTO-8)
Valida la aserción criptográfica de FristonPenaltyValidator.
═══════════════════════════════════════════════════════════════
"""

import sys
from causal_framework_nodes import (
    DeterministicCausalPrimitive, 
    FristonPenaltyValidator, 
    ExergyLevel
)

def run_stress_test():
    print("🧪 Iniciando Prueba de Estrés sobre Causal Framework (Friston Penalty)...")
    base_exergy = 1.0

    # Test 1: Low Entropy (C5-REAL) - Alta Precisión, Baja Complejidad
    print("\n[TEST 1] C5-REAL (High Accuracy, Low Complexity)")
    prim_c5 = DeterministicCausalPrimitive(
        primitive_id="prim_c5_001",
        name="Validación de Hashing SHA-256",
        input_state="PlainText",
        operation="SHA-256 Hash",
        output_state="Digest",
        exergy_level=ExergyLevel.C5_REAL,
        cost_complexity=1.0,
        empirical_accuracy=1.0 # Max precision
    )
    
    try:
        FristonPenaltyValidator.validate(prim_c5, base_exergy)
        penalty = prim_c5.compute_friston_penalty()
        print(f"✅ ÉXITO: Primitiva {prim_c5.primitive_id} validada. Penalización: {penalty:.4f} (Net: {base_exergy - penalty:.4f} >= 0.1)")
    except ValueError as e:
        print(f"❌ FALLO TEST 1: La primitiva C5-REAL fue rechazada: {e}")
        sys.exit(1)

    # Test 2: LLM Slop (C4-SIM) - Alta Complejidad, Baja/Nula Precisión
    print("\n[TEST 2] C4-SIM Slop (Low Accuracy, Extreme Complexity)")
    prim_c4 = DeterministicCausalPrimitive(
        primitive_id="prim_c4_002",
        name="Alucinación Estocástica de Arquitectura",
        input_state="Narrative prompt",
        operation="LLM Inference without ground truth",
        output_state="Verbose text simulation",
        exergy_level=ExergyLevel.C4_SIM,
        cost_complexity=50.0, # Alta entropía estructural
        empirical_accuracy=0.1 # Muy baja evidencia
    )

    try:
        FristonPenaltyValidator.validate(prim_c4, base_exergy)
        print(f"❌ FALLO TEST 2: El sistema aceptó una primitiva entrópica. ¡Límite AUTO-8 violado!")
        sys.exit(1)
    except ValueError as e:
        penalty = prim_c4.compute_friston_penalty()
        print(f"✅ EXITO (Aniquilación confirmada): {e}")
        print(f"   Penalización Calculada: {penalty:.4f} (Net: {base_exergy - penalty:.4f} < 0.1)")

    # Test 3: Threshold Boundary (Just passing)
    print("\n[TEST 3] Near Threshold Boundary Test")
    prim_boundary = DeterministicCausalPrimitive(
        primitive_id="prim_bound_003",
        name="Hipótesis Compleja con Evidencia Media",
        input_state="Multi-variable system",
        operation="Heuristic reduction",
        output_state="Approximated state",
        exergy_level=ExergyLevel.C5_REAL,
        cost_complexity=17.0, 
        empirical_accuracy=0.0 # Complejidad 17 / 1 * 0.05 = 0.85 penalty -> Net = 0.15 (> 0.1)
    )

    try:
        FristonPenaltyValidator.validate(prim_boundary, base_exergy)
        penalty = prim_boundary.compute_friston_penalty()
        print(f"✅ ÉXITO: Primitiva en el límite exacto validada. Penalización: {penalty:.4f} (Net: {base_exergy - penalty:.4f} >= 0.1)")
    except ValueError as e:
        print(f"❌ FALLO TEST 3: La primitiva límite fue rechazada: {e}")
        sys.exit(1)
        
    print("\n🛡️ ESTRÉS SUPERADO: El Causal Framework repele activamente el colapso termodinámico.")

if __name__ == "__main__":
    run_stress_test()
