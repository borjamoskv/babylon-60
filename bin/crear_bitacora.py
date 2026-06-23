#!/usr/bin/env python3
import argparse
import datetime
import os
import subprocess

ADR_DIR = "docs/ADR"

def get_current_git_hash():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "HASH_PENDIENTE"

def create_adr(title, context, decision):
    os.makedirs(ADR_DIR, exist_ok=True)
    files = [f for f in os.listdir(ADR_DIR) if f.startswith("ADR-") and f.endswith(".md")]
    next_num = len(files) + 1
    
    clean_title = "".join(c if c.isalnum() else "_" for c in title).lower()
    clean_title = "_".join(filter(None, clean_title.split("_")))
    
    file_name = f"ADR-{next_num:03d}-{clean_title}.md"
    file_path = os.path.join(ADR_DIR, file_name)

    date_str = datetime.datetime.now().strftime("%B %Y")
    git_hash = get_current_git_hash()

    content = f"""# ADR-{next_num:03d}: {title}

**Fecha:** {date_str}
**Hash Origen:** `{git_hash}`
**Autor:** Borja Moskv / MOSKV-1 APEX

## 1. Contexto (El Problema Físico/Epistémico)
{context}

## 2. Decisión (La Solución)
{decision}

## 3. Consecuencias
[Impacto esperado en la arquitectura y flujo exergético del sistema]
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    # Update index
    index_path = os.path.join(ADR_DIR, "000-index.md")
    if os.path.exists(index_path):
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(f"| ADR-{next_num:03d} | {title} | {date_str} | `{git_hash}` | Borja Moskv |\n")
    
    print(f"[C5-REAL] Bitácora registrada: {file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inyectar nuevo registro en la Bitácora Ontológica (ADR)")
    parser.add_argument("title", help="Título del componente o decisión")
    parser.add_argument("--context", default="[Completar contexto termodinámico/epistémico]", help="Problema que se resuelve")
    parser.add_argument("--decision", default="[Completar arquitectura de la solución]", help="Diseño de la solución")
    
    args = parser.parse_args()
    create_adr(args.title, args.context, args.decision)
