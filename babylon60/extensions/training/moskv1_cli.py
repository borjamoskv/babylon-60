#!/usr/bin/env python3
# [C5-REAL] Exergy-Maximized
# Author: borjamoskv
# License: Apache-2.0
"""
MOSKV-1 CLI — Interfaz de línea de comandos para el Kernel Cognitivo Híbrido.

Commands:
    compile   — Compilar dataset instruccional desde CORTEX
    train     — Ejecutar LoRA fine-tuning con MLX
    register  — Registrar modelo en Ollama
    infer     — Ejecutar inferencia híbrida (RAG + LoRA)
    stats     — Mostrar estadísticas del dataset compilado
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


def cmd_compile(workspace: str | None = None) -> None:
    """Compile the full MOSKV-1 training dataset."""
    from babylon60.extensions.training.moskv1_dataset_compiler import MOSKV1DatasetCompiler

    ws = Path(workspace) if workspace else Path.cwd()
    compiler = MOSKV1DatasetCompiler(workspace_path=ws)

    print("🔧 MOSKV-1 Dataset Compilation — C5-REAL")
    print(f"   Workspace: {ws}")
    print()

    stats = compiler.compile_full_dataset()

    # Export in both formats
    sharegpt_path = compiler.export_sharegpt()
    alpaca_path = compiler.export_alpaca()

    print()
    print("═══ COMPILATION STATS ═══")
    print(compiler.get_stats_yaml())
    print()
    print(f"📁 ShareGPT: {sharegpt_path}")
    print(f"📁 Alpaca:   {alpaca_path}")


def cmd_train(
    model: str = "mlx-community/Qwen2.5-Coder-32B-Instruct-4bit",
    iters: int = 1000,
    batch_size: int = 2,
    lora_rank: int = 32,
    lora_layers: int = 16,
    learning_rate: float = 2e-5,
) -> None:
    """Execute MLX LoRA fine-tuning."""
    import subprocess

    dataset_dir = Path.home() / ".cortex" / "training" / "datasets"
    adapter_path = Path.home() / ".cortex" / "training" / "adapters"
    adapter_path.mkdir(parents=True, exist_ok=True)

    if not (dataset_dir / "moskv1_dataset.jsonl").exists():
        print("❌ Dataset not found. Run 'compile' first.")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "mlx_lm.lora",
        "--model", model,
        "--data", str(dataset_dir),
        "--adapter-path", str(adapter_path),
        "--iters", str(iters),
        "--batch-size", str(batch_size),
        "--lora-layers", str(lora_layers),
        "--lora-rank", str(lora_rank),
        "--learning-rate", str(learning_rate),
    ]

    print(f"🧠 MLX LoRA Training — {model}")
    print(f"   Iterations: {iters} | Batch: {batch_size} | Rank: {lora_rank}")
    print(f"   Output: {adapter_path}")
    print()

    result = subprocess.run(cmd, text=True)
    sys.exit(result.returncode)


def cmd_register() -> None:
    """Register MOSKV-1 model in Ollama."""
    from babylon60.extensions.training.moskv1_core import MOSKV1Core

    core = MOSKV1Core()
    modelfile = core.get_modelfile()

    modelfile_path = Path.home() / ".cortex" / "training" / "adapters" / "Modelfile"
    modelfile_path.parent.mkdir(parents=True, exist_ok=True)
    modelfile_path.write_text(modelfile, encoding="utf-8")

    print(f"📄 Modelfile written to: {modelfile_path}")
    print()
    print("To register in Ollama, run:")
    print(f"  ollama create moskv1-core -f {modelfile_path}")


def cmd_stats() -> None:
    """Show stats of the last compiled dataset."""
    dataset_path = Path.home() / ".cortex" / "training" / "datasets" / "moskv1_dataset.jsonl"
    if not dataset_path.exists():
        print("❌ No compiled dataset found.")
        sys.exit(1)

    entries = []
    with open(dataset_path, encoding="utf-8") as f:
        for line in f:
            entries.append(json.loads(line))

    total_tokens = sum(
        sum(len(m.get("content", "")) for m in e.get("conversations", []))
        for e in entries
    ) // 4

    print(f"📊 Dataset: {dataset_path}")
    print(f"   Entries: {len(entries)}")
    print(f"   Estimated tokens: {total_tokens:,}")
    print(f"   File size: {dataset_path.stat().st_size / 1024:.1f} KB")


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m babylon60.extensions.training.moskv1_cli <command>")
        print()
        print("Commands:")
        print("  compile   Compile CORTEX knowledge into training dataset")
        print("  train     Run MLX LoRA fine-tuning")
        print("  register  Generate Ollama Modelfile")
        print("  stats     Show dataset statistics")
        sys.exit(1)

    command = sys.argv[1]

    if command == "compile":
        workspace = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_compile(workspace)
    elif command == "train":
        cmd_train()
    elif command == "register":
        cmd_register()
    elif command == "stats":
        cmd_stats()
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
