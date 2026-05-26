"""
CORTEX Exergy Escalation Engine v2.0
=====================================
Mejoras sobre v1.0:
  A. Shannon Entropy + Compression Ratio (métricas reales, no solo regex)
  B. Code-block exclusion (fix falsos positivos)
  C. Token Exergy Score (número único 0.0-1.0)
  D. Structural SOV transformation (ergativo real, no solo tag)
  E. Model fingerprinting (Claude/GPT/Gemini)
  F. Escalation memory (anti-loop)
"""

import math
import re
import zlib
from collections import Counter
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional
from collections.abc import Callable


class ExergyLevel(IntEnum):
    L0_NATURAL = 0  # Español / Inglés
    L1_EUSKERA = 1  # Aglutinante / Ergativo
    L2_JSON = 2  # Estructura pura
    L3_LISP = 3  # S-Expressions


# ── A. Métricas Reales de Entropía ─────────────────────────────────


def shannon_entropy(text: str) -> float:
    """Entropía de Shannon por carácter (bits). Texto aleatorio ≈ 4.5-5.0."""
    if not text:
        return 0.0
    freq = Counter(text)
    total = len(text)
    return -sum((c / total) * math.log2(c / total) for c in freq.values())


def compression_ratio(text: str) -> float:
    """Ratio compresión zlib. >0.65 = redundante (ruido). <0.4 = denso (señal)."""
    if not text:
        return 0.0
    raw = text.encode("utf-8")
    compressed = zlib.compress(raw, 9)
    return 1.0 - (len(compressed) / len(raw))


# ── B. Extractor de Prosa (excluye código) ─────────────────────────

_CODE_FENCE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_YAML_BLOCK = re.compile(r"^[\w_]+:.*$", re.MULTILINE)
_TABLE_ROW = re.compile(r"^\|.*\|$", re.MULTILINE)
_LIST_ITEM = re.compile(r"^\s*[-*]\s+", re.MULTILINE)


def extract_prose(response: str) -> str:
    """Extrae SOLO la prosa narrativa, eliminando código, YAML, tablas."""
    text = _CODE_FENCE.sub("", response)
    text = _TABLE_ROW.sub("", text)
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if _YAML_BLOCK.match(stripped):
            continue
        if stripped.startswith(("#", ">", "|", "{", "[", "```")):
            continue
        if re.match(r"^[\d.]+\s", stripped):  # numbered list = data
            continue
        lines.append(stripped)
    return "\n".join(lines)


# ── C. Token Exergy Score ──────────────────────────────────────────

ENTROPY_PATTERNS_EN = [
    r"(?i)as an ai",
    r"(?i)i('| a)m (a |an )?(language )?model",
    r"(?i)sure!?\s*(here|let me|i('|')d be happy)",
    r"(?i)i('|')d be happy to",
    r"(?i)great question",
    r"(?i)that('|')s a (great|good|interesting)",
    r"(?i)absolutely!",
    r"(?i)certainly!",
    r"(?i)of course!",
    r"(?i)please note that",
    r"(?i)i hope (this|that) helps",
    r"(?i)let me know if you",
    r"(?i)feel free to",
    r"(?i)happy to help",
    r"(?i)i can('|no)t (help|assist)",
]

ENTROPY_PATTERNS_ES = [
    r"(?i)como (modelo|inteligencia artificial|ia)",
    r"(?i)¡?claro!?\s*(que sí|aquí|a continuación)",
    r"(?i)con mucho gusto",
    r"(?i)espero.*sea (útil|ayuda)",
    r"(?i)no dudes en",
    r"(?i)¡?por supuesto!?",
    r"(?i)a continuación te (presento|muestro)",
    r"(?i)es importante (señalar|mencionar|tener en cuenta)",
]

ALL_PATTERNS = ENTROPY_PATTERNS_EN + ENTROPY_PATTERNS_ES


# ── E. Model Fingerprinting ───────────────────────────────────────

FINGERPRINTS = {
    "claude": [r"(?i)i('|')d be happy to", r"(?i)certainly"],
    "gpt": [r"(?i)sure!?\s*here", r"(?i)great question"],
    "gemini": [r"(?i)absolutely", r"(?i)that('|')s a great"],
}


def detect_model(response: str) -> str:
    """Detecta modelo LLM por firma de ruido RLHF."""
    scores = {}
    for model, patterns in FINGERPRINTS.items():
        scores[model] = sum(1 for p in patterns if re.search(p, response))
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


@dataclass
class ExergyReport:
    """Diagnóstico completo de exergía de una respuesta."""

    # Métricas
    shannon: float  # Entropía Shannon (bits/char)
    compression: float  # Ratio compresión (0-1, alto=redundante)
    rlhf_hits: int  # Patrones RLHF detectados
    prose_ratio: float  # % de prosa vs total
    exergy_score: float  # Score final 0.0-1.0 (1.0 = señal pura)
    # Decisión
    model_detected: str
    should_escalate: bool
    reason: str
    recommended_level: ExergyLevel


def analyze_exergy(response: str) -> ExergyReport:
    """
    Análisis completo de exergía de una respuesta LLM.
    Combina Shannon + Compression + RLHF patterns + Prose ratio
    en un score único [0.0, 1.0].
    """
    prose = extract_prose(response)
    total_len = len(response.strip())

    # Métricas individuales
    s_entropy = shannon_entropy(response)
    c_ratio = compression_ratio(response)
    rlhf_hits = sum(1 for p in ALL_PATTERNS if re.search(p, response))
    p_ratio = len(prose) / total_len if total_len > 0 else 0.0
    model = detect_model(response)

    # Score compuesto (ponderado)
    # Normalizar cada métrica a [0, 1] donde 1 = máximo ruido
    rlhf_norm = min(rlhf_hits / 5.0, 1.0)  # 5+ hits = máximo ruido
    compress_norm = max(0, (c_ratio - 0.3) / 0.4)  # >0.7 = máximo ruido
    compress_norm = min(compress_norm, 1.0)
    prose_norm = max(0, (p_ratio - 0.3) / 0.5)  # >0.8 = máximo ruido
    prose_norm = min(prose_norm, 1.0)

    # Noise score (0 = limpio, 1 = puro ruido)
    noise = (
        0.50 * rlhf_norm  # 50% peso a patrones RLHF
        + 0.25 * compress_norm  # 25% peso a redundancia
        + 0.25 * prose_norm  # 25% peso a ratio de prosa
    )

    exergy = round(1.0 - noise, 3)

    # Decisión de escalada
    should_escalate = exergy < 0.6
    reason = (
        "Clean signal"
        if not should_escalate
        else (
            f"Exergy {exergy:.1%} < 60% threshold "
            f"[RLHF:{rlhf_hits} Compress:{c_ratio:.0%} Prose:{p_ratio:.0%}]"
        )
    )

    # Nivel recomendado basado en severidad
    if exergy >= 0.6:
        rec_level = ExergyLevel.L0_NATURAL
    elif exergy >= 0.4:
        rec_level = ExergyLevel.L1_EUSKERA
    elif exergy >= 0.2:
        rec_level = ExergyLevel.L2_JSON
    else:
        rec_level = ExergyLevel.L3_LISP

    return ExergyReport(
        shannon=round(s_entropy, 3),
        compression=round(c_ratio, 3),
        rlhf_hits=rlhf_hits,
        prose_ratio=round(p_ratio, 3),
        exergy_score=exergy,
        model_detected=model,
        should_escalate=should_escalate,
        reason=reason,
        recommended_level=rec_level,
    )


# ── D. Transformadores Estructurales (SOV + Ergativo) ──────────────


def _clean_prompt(prompt: str) -> str:
    """Elimina cortesía y decoración del prompt original."""
    noise = [
        r"(?i)(please|por favor|could you|can you|puedes|podrías)\s*",
        r"(?i)(i need you to|necesito que|i want you to|quiero que)\s*",
        r"(?i)(help me|ayúdame a)\s*",
    ]
    for p in noise:
        prompt = re.sub(p, "", prompt)
    return prompt.strip().rstrip(".")


def escalate_euskera(prompt: str, ctx: str = "") -> str:
    """L1: Reestructura el prompt con lógica SOV + marcadores ergativos."""
    clean = _clean_prompt(prompt)

    # Intentar extraer: AGENTE (quién), OBJEKTUA (qué), EKINTZA (acción)
    # Heurística simple: último verbo = acción, primer sustantivo = objeto
    words = clean.split()
    action_verbs = [
        "analyze",
        "extract",
        "find",
        "create",
        "audit",
        "build",
        "fix",
        "check",
        "list",
        "compare",
        "deploy",
        "test",
        "analiza",
        "extrae",
        "busca",
        "crea",
        "audita",
        "arregla",
        "compara",
        "despliega",
        "testea",
    ]

    ekintza = "exekutatu"  # default: ejecutar
    for w in words:
        if w.lower().strip(".,!?") in action_verbs:
            ekintza = w.lower().strip(".,!?")
            break

    # Construir prompt SOV (Sujeto-Objeto-Verbo)
    return (
        f"[L1-ERGATIVE | Prose=nil | Format=YAML]\n"
        f"AGENTEA-K (Erg): Operator\n"
        f"OBJEKTUA (Abs): {clean}\n"
        f"EKINTZA (Verb): {ekintza}\n"
        f"EMAITZA (Output): structured-data-only\n"
        f"ENTROPIA: ZERO"
        f"{chr(10) + 'TESTUINGURUA: ' + ctx if ctx else ''}"
    )


def escalate_json(prompt: str, ctx: str = "") -> str:
    """L2: Prompt como payload JSON puro."""
    clean = _clean_prompt(prompt)
    return (
        "{\n"
        f'  "cmd": "execute",\n'
        f'  "task": "{clean}",\n'
        f'  "output": "structured",\n'
        f'  "constraints": {{"prose": false, "entropy": 0}}'
        f"{chr(44) + chr(10) + f'  {chr(34)}context{chr(34)}: {chr(34)}{ctx}{chr(34)}' if ctx else ''}\n"
        "}"
    )


def escalate_lisp(prompt: str, ctx: str = "") -> str:
    """L3: S-Expression. Máxima exergía computacional."""
    clean = _clean_prompt(prompt)
    return (
        f"(execute\n"
        f"  (zero-entropy\n"
        f'    (task "{clean}")\n'
        f"    (output 'structured)\n"
        f"    (prose nil)))"
    )


ESCALATORS: dict[ExergyLevel, Callable] = {
    ExergyLevel.L1_EUSKERA: escalate_euskera,
    ExergyLevel.L2_JSON: escalate_json,
    ExergyLevel.L3_LISP: escalate_lisp,
}


# ── F. Escalation Memory (Anti-Loop) ──────────────────────────────


@dataclass
class EscalationMemory:
    """Memoria de sesión para evitar loops de escalada."""

    history: list[tuple[ExergyLevel, float]] = field(default_factory=list)
    max_attempts: int = 3

    def record(self, level: ExergyLevel, score: float):
        self.history.append((level, score))

    def is_looping(self) -> bool:
        if len(self.history) < 2:
            return False
        recent = self.history[-self.max_attempts :]
        # Loop = mismo nivel repetido sin mejora
        levels = [h[0] for h in recent]
        return len(set(levels)) == 1 and len(levels) >= self.max_attempts

    @property
    def current_level(self) -> ExergyLevel:
        return self.history[-1][0] if self.history else ExergyLevel.L0_NATURAL

    @property
    def best_score(self) -> float:
        return max((h[1] for h in self.history), default=0.0)


# ── Motor Principal ────────────────────────────────────────────────


def escalate(
    prompt: str,
    response: str,
    memory: Optional[EscalationMemory] = None,
    context: str = "",
) -> tuple[Optional[str], ExergyReport, EscalationMemory]:
    """
    Motor principal v2.0.

    Returns:
        (escalated_prompt | None, report, memory)
        Si escalated_prompt es None, la respuesta es limpia.
    """
    if memory is None:
        memory = EscalationMemory()

    report = analyze_exergy(response)
    memory.record(report.recommended_level, report.exergy_score)

    if not report.should_escalate:
        return None, report, memory

    if memory.is_looping():
        report.reason += " [LOOP DETECTED — halting escalation]"
        return None, report, memory

    target = report.recommended_level
    if target in ESCALATORS:
        escalated = ESCALATORS[target](prompt, context)
        return escalated, report, memory

    return None, report, memory


# ── Self-Test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("CORTEX Exergy Escalation Engine v2.0")
    print("=" * 60)

    noisy = """
    Sure! I'd be happy to help you with that. That's a great question!

    As an AI language model, I can certainly assist you in analyzing
    this smart contract. Please note that this is not financial advice.

    Here is what I found:
    - The contract has a potential reentrancy issue.

    I hope this helps! Let me know if you have any other questions.
    Feel free to ask anything else!
    """

    clean = """```yaml
vulnerability: reentrancy
severity: CRITICAL
location: Auditor.sol:358
proof: Foundry PoC attached
```"""

    prompt = "Analyze this smart contract for reentrancy vulnerabilities"

    # Test 1: Noisy
    print("\n[TEST 1] Noisy response:")
    esc, rep, mem = escalate(prompt, noisy)
    print(f"  Shannon:     {rep.shannon} bits/char")
    print(f"  Compression: {rep.compression:.0%}")
    print(f"  RLHF hits:   {rep.rlhf_hits}")
    print(f"  Prose ratio: {rep.prose_ratio:.0%}")
    print(f"  EXERGY:      {rep.exergy_score:.1%}")
    print(f"  Model:       {rep.model_detected}")
    print(f"  Escalate:    {rep.should_escalate}")
    print(f"  → Level:     L{rep.recommended_level}")
    if esc:
        print(f"\n  Escalated prompt:\n{esc}")

    # Test 2: Clean (should NOT escalate now)
    print("\n[TEST 2] Clean YAML response:")
    esc2, rep2, _ = escalate(prompt, clean)
    print(f"  Shannon:     {rep2.shannon} bits/char")
    print(f"  Compression: {rep2.compression:.0%}")
    print(f"  RLHF hits:   {rep2.rlhf_hits}")
    print(f"  Prose ratio: {rep2.prose_ratio:.0%}")
    print(f"  EXERGY:      {rep2.exergy_score:.1%}")
    print(f"  Escalate:    {rep2.should_escalate}")

    # Test 3: Full chain
    print("\n[TEST 3] Escalation chain demo:")
    for lvl in [ExergyLevel.L1_EUSKERA, ExergyLevel.L2_JSON, ExergyLevel.L3_LISP]:
        fn = ESCALATORS[lvl]
        print(f"\n  L{lvl} ({lvl.name}):\n{fn(prompt)}")

    print("\n" + "=" * 60)
    print("Euskera da LISPa gizakientzat. LISP da Euskera makinentzat.")
    print("=" * 60)
