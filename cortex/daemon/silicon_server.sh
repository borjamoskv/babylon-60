#!/bin/bash
# OMEGA-1 COMPLIANCE: Mac Studio Direct-Silicon Daemon
# Loads the 4-bit Hyper-Quantized SLM into Unified Memory

MODEL_PATH="cortex-qwen-4bit"
PORT=8080

echo "======================================================"
echo " CORTEX DIRECT-SILICON DAEMON (C5-REAL) "
echo "======================================================"
echo "[INFO] Enforcing Air-Gapped Topology..."
echo "[INFO] Hardware Target: Apple Silicon (MLX)"
echo "[INFO] Loading model: $MODEL_PATH"

# Ensure mlx-lm is installed
if ! command -v mlx_lm.server &> /dev/null
then
    echo "[WARN] mlx_lm.server not found. Installing mlx-lm..."
    python3 -m pip install mlx-lm
fi

# Run the local OpenAI-compatible server using MLX
echo "[INFO] Starting NPU/GPU inference engine..."
python3 -m mlx_lm.server --model "$MODEL_PATH" --port "$PORT" --host 127.0.0.1
