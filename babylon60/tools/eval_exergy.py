#!/usr/bin/env python3
"""
babylon60/tools/eval_exergy.py
Proxy heurístico para medición de E_eff y DOLA bajo protocolo Ouroboros.
C5-REAL: Solo utiliza métricas cuantificables en texto plano. Sin efectos secundarios.
"""

import json
import re
import sys
from pathlib import Path

try:
    from pydantic import BaseModel, Field
except ImportError:
    print("ERROR: pydantic not installed. Run: pip install pydantic", file=sys.stderr)
    sys.exit(1)


class TokenProxy:
    """Aproximación ligera de tokenización para análisis estático."""

    def count(self, text: str) -> int:
        return max(1, len(text.split()))


class ExergyMetric(BaseModel):
    token_count: int = Field(..., gt=0)
    info_density: float = Field(..., ge=0.0, le=1000.0)
    dola_trigger: float = Field(..., ge=0.0, le=1.0)
    heuristics: dict[str, float] = Field(default_factory=dict)


def calculate_eff(text: str) -> tuple[float, float]:
    """Proxy E_eff: Retorna (info_density, ttr) para evitar recálculo o NameError."""
    tokens = TokenProxy().count(text)
    if tokens == 0:
        return 0.0, 0.0

    words = re.findall(r"\b\w+\b", text.lower())
    unique = len(set(words))
    ttr = unique / max(1, len(words))

    struct_markers = len(
        re.findall(r"(^\s*[-*•]|\`\`\`|^\s*#\s|^\s*\[|^\s*\])", text, re.MULTILINE)
    )
    struct_ratio = min(struct_markers / max(1, tokens * 0.1), 1.0)

    filler = len(
        re.findall(
            r"\b(solo que|básicamente|en resumen|por lo tanto|sin embargo|además)\b", text.lower()
        )
    )
    filler_pen = max(0.0, 1.0 - (filler * 0.15))

    raw = (ttr * 400) + (struct_ratio * 400) + (100 * filler_pen)
    info_density = min(round(raw, 1), 1000.0)

    return info_density, round(ttr, 3)


def calculate_dola(text: str) -> float:
    """Proxy DOLA: Detección de triggers de razonamiento multi-paso."""
    triggers = [
        r"(revisión|validación|auditoría|verificación|check|assert|valid)",
        r"(si.*entonces|por.*lo.*tanto|alternativamente|en.*cambio)",
        r"(layer\s*[abc]|capa\s*[abc]|fase\s*\d|paso\s*\d)",
        r"(pydantic|zod|serde|ruff|pytest|mypy)",
        r"(calibrated|uncertainty|conditioned|heurística|proxy)",
    ]
    hits = sum(len(re.findall(pat, text, re.IGNORECASE)) for pat in triggers)
    return min(round(hits / 8.0, 2), 1.0)


def main():
    if len(sys.argv) < 2:
        print("Usage: python eval_exergy.py <response_text> [ledger_path]", file=sys.stderr)
        sys.exit(1)

    text = sys.argv[1]
    ledger_path = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else Path("babylon60/logs/exergy_ledger.json")
    )

    tokens = TokenProxy().count(text)
    eff, ttr = calculate_eff(text)
    dola = calculate_dola(text)

    struct_contrib = round(max(0.0, eff - ttr * 400) * 0.5, 2)

    record = ExergyMetric(
        token_count=tokens,
        info_density=eff,
        dola_trigger=dola,
        heuristics={"ttr": ttr, "struct": struct_contrib},
    )

    if ledger_path.exists():
        with open(ledger_path, encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []

    history.append(
        {
            "id": f"eval-{len(history) + 1:04d}",
            "eff": record.info_density,
            "dola": record.dola_trigger,
            "tokens": record.token_count,
            "heuristics": record.heuristics,
            "confidence": "Calibrated Uncertainty",
        }
    )

    ledger_path.parent.mkdir(parents=True, exist_ok=True)

    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print(f"✅ E_eff: {eff} | DOLA: {dola} | Tokens: {tokens} | TTR: {ttr}")
    print(f"📦 Ledger updated: {ledger_path}")


if __name__ == "__main__":
    main()
