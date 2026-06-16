#!/usr/bin/env bash
# ==============================================================================
# MAXWELL_DEMON_ROUTER.sh (L1)
# STATE: C5-REAL | AESTHETIC: INDUSTRIAL_NOIR_2026
# Derived from: AUTODIDACT_THERMODYNAMICS.md
# Purpose: Compresses LLM context by stripping narrative entropy before execution.
# ==============================================================================
set -euo pipefail

INPUT_FILE="${1:-/dev/stdin}"
OUTPUT_FILE="${2:-/dev/stdout}"

# The Demon strips out common narrative fillers and retains only structural YAML/JSON/Code.
# In a full C5-REAL deployment, this passes through a local MLX model (L1).
echo "[MAXWELL-DEMON] Iniciando Compresión Termodinámica L1..." >&2

# Anergic Stop-Words Purge (Regex stripping)
cat "$INPUT_FILE" | grep -vE "^(I think|Here is|Sure,|As an AI|Let's begin|Understood|Okay|I understand)" \
    | awk '
    BEGIN { in_code = 0 }
    /^```/ { in_code = !in_code; print; next }
    in_code { print; next }
    # Outside code blocks, keep only high density structures (headers, lists, JSON)
    /^#|^- |^\{|^\[|^[A-Z_]+:/ { print }
    ' > "$OUTPUT_FILE"

echo "[MAXWELL-DEMON] Entropía Purgada. Contexto comprimido a Señal Pura." >&2
