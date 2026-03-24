"""CHRONOS-1 Yield Calculus (Axiom Ω₁₁).

Extracted from heal.py to maintain thermodynamic LOC limits.
"""

from dataclasses import dataclass

from cortex.extensions.mejoralo.constants import (
    CHRONOS_COMPLEXITY_DIVISOR,
    CHRONOS_HOURS_PER_CODEPATH,
    CHRONOS_HOURS_PER_FILE,
)


@dataclass
class ChronosYield:
    """Structured representation of thermodynamic yield (Axiom Ω₉)."""

    hours: float
    claim_text: str


def calculate_chronos_yield(
    files_touched: int,
    codepaths_affected: int,
    runtime_ms: int,
    cyclomatic_complexity_delta: int,
) -> ChronosYield:
    """Calculate linear hours saved per the CHRONOS-1 formula (Axiom Ω₁₁).

    Hours_Saved = ((files_touched * 6) + (codepaths_affected * 12)
                  + (runtime_ms * 10)) * (complexity_delta / 3) / 60
    """
    divisor = max(1, CHRONOS_COMPLEXITY_DIVISOR)
    complexity_factor = abs(cyclomatic_complexity_delta) / divisor
    raw = (
        (files_touched * CHRONOS_HOURS_PER_FILE)
        + (codepaths_affected * CHRONOS_HOURS_PER_CODEPATH)
        + (runtime_ms * 10)
    ) * complexity_factor
    hours = round(float(raw) / 60.0, 2)

    min_range = max(0.1, round(float(hours) * 0.8, 2))
    max_range = round(float(hours) * 1.2, 2)

    claim_text = (
        f"Claim: {hours}h saved\n"
        "Justificación:\n"
        f"  - Base: Fórmula CHRONOS-1 con (files_touched={files_touched}, "
        f"codepaths={codepaths_affected}, runtime_ms={runtime_ms}, "
        f"cyclomatic_delta={cyclomatic_complexity_delta})\n"
        f"  - Variables: r=0 (base yield), d={divisor} (divisor), n=1 (iteración)\n"
        f"  - Rango: [{min_range}h, {max_range}h] según inercia termodinámica\n"
        "  - Confianza: C5-Dynamic"
    )

    return ChronosYield(hours=hours, claim_text=claim_text)
