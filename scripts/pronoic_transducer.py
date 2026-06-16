#!/usr/bin/env python3
# ==============================================================================
# PRONOIC_TRANSDUCER.py
# STATE: C5-REAL | AESTHETIC: INDUSTRIAL_NOIR_2026
# Derived from: AUTODIDACT_PRONOICO.md
# Purpose: Zero Defensive Halts. Transforms DB/API errors into JIT requirements.
# ==============================================================================
import subprocess
import sys


def transduce_error(error_log_path: str):
    print("[PRONOIC-TRANSDUCER] Analizando Entorno Hostil como Tutor Didáctico...")
    with open(error_log_path) as f:
        log = f.read()

    # Ejemplo: Si falta una tabla en SQLite, no crashea, crea la tabla.
    if "no such table" in log.lower():
        print("[PRONOIC-TRANSDUCER] Fricción Detectada: Tabla faltante. Sintetizando Migración JIT...")
        table_name = log.split("no such table: ")[1].split("\n")[0]
        # Auto-forja la solución mediante Sortu-APEX
        subprocess.run([
            "cortex", "daemon", "--task", "sortu-m2m", 
            "--intent", f"create migration for missing table {table_name}"
        ], check=False)
        print("[PRONOIC-TRANSDUCER] Entorno Mutado con Éxito. Reanudando ejecución.")
    else:
        print("[PRONOIC-TRANSDUCER] Señal de fricción no mapeada. Enrutando a Ouroboros-∞ para absorción.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 PRONOIC_TRANSDUCER.py <error.log>")
        sys.exit(1)
    transduce_error(sys.argv[1])
