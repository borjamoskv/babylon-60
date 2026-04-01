from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger("cortex.extensions.swarm.crystal_thermometer")

Quadrant = Literal["ACTIVE", "FOUNDATIONAL", "NOISE", "DEAD_WEIGHT"]
Recommendation = Literal["MAINTAIN", "PROTECT", "DECAY", "PURGE", "MERGE", "PROMOTE"]

TEMPERATURE_HOT = 0.1
TEMPERATURE_COLD = 0.01
RESONANCE_HIGH = 0.5
RESONANCE_LOW = 0.2
AXIOMATIC_INERTIA_THRESHOLD = 0.8
TEMPERATURE_TIBIA = 0.1
MIN_AGE_DAYS_FOR_PURGE = 14
MIN_AGE_DAYS_FOR_PROMOTE = 7

AXIOM_TEXTS = [
    "Self-reference: if I write it, I execute it. Autonomous systems.",
    "Multi-scale causality: wrong scale, not wrong place. Architecture patterns.",
    "Entropic asymmetry: does it reduce or displace entropy. Information theory.",
    "Byzantine default: verify then trust, never reversed. Security validation.",
    "Aesthetic integrity: ugly equals incomplete. Design systems UI UX.",
    "Antifragile by default: what antibody does this failure forge. Error recovery.",
    "Zenon's razor: did the conclusion mutate? Execute. Decision making.",
]


@dataclass
class CrystalVitals:
    fact_id: str
    content_preview: str
    temperature: float
    resonance: float
    quadrant: Quadrant
    recommendation: Recommendation
    age_days: float
    recall_count: int
    is_diamond: bool
    project_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ThermodynamicYield:
    tokens_saved: int
    cpu_cycles_saved: int
    llm_inference_cost: int
    net_score: float
    is_profitable: bool
    abort_reason: str = ""


def evaluate_net_yield(
    tokens_saved: int,
    cpu_cycles_saved: int,
    llm_inference_cost: int,
) -> ThermodynamicYield:
    """Calcula el saldo exergético (Yield Neto) para mutaciones MCTS.

    Axioma Ω3: gasto > reducción de entropía → rama aniquilada.
    """
    score = (tokens_saved + (cpu_cycles_saved * 0.0001)) - llm_inference_cost
    is_profitable = score > 0
    reason = (
        ""
        if is_profitable
        else f"Saldo negativo ({score:.2f}). Cost > Savings."
    )

    if not is_profitable:
        logger.warning(
            "🧊 [THERMOMETER] Yield Negativo: %s", reason,
        )
    else:
        logger.info(
            "🔥 [THERMOMETER] Mutación rentable: %s score", score,
        )

    return ThermodynamicYield(
        tokens_saved=tokens_saved,
        cpu_cycles_saved=cpu_cycles_saved,
        llm_inference_cost=llm_inference_cost,
        net_score=score,
        is_profitable=is_profitable,
        abort_reason=reason,
    )


def calculate_temperature(recall_count: int, age_days: float) -> float:
    if age_days >= 0.01:
        return recall_count / max(age_days, 1.0)
    return float(recall_count) if recall_count > 0 else 0.5


async def calculate_resonance(
    content_embedding: list[float], axiom_embeddings: list[list[float]]
) -> float:
    if not content_embedding or not axiom_embeddings:
        return 0.0

    try:
        import numpy as np

        content_vec = np.array(content_embedding, dtype=np.float32)
        content_norm = np.linalg.norm(content_vec)
        if content_norm < 1e-10:
            return 0.0

        max_sim = max(
            np.dot(content_vec, np.array(axiom_emb, dtype=np.float32))
            / (content_norm * np.linalg.norm(np.array(axiom_emb, dtype=np.float32)))
            for axiom_emb in axiom_embeddings
            if np.linalg.norm(np.array(axiom_emb, dtype=np.float32)) >= 1e-10
        )
        return max_sim
    except Exception as e:
        logger.error("Resonance calculation failed: %s", e)
        return 0.0


def classify_quadrant(temperature: float, resonance: float) -> Quadrant:
    if temperature >= TEMPERATURE_HOT:
        return "ACTIVE" if resonance >= RESONANCE_HIGH else "NOISE"
    return "FOUNDATIONAL" if resonance >= RESONANCE_HIGH else "DEAD_WEIGHT"


def determine_recommendation(
    quadrant: Quadrant, is_diamond: bool, age_days: float, temperature: float, resonance: float
) -> Recommendation:
    if quadrant == "ACTIVE":
        if not is_diamond and age_days >= MIN_AGE_DAYS_FOR_PROMOTE and resonance > 0.6:
            return "PROMOTE"
        return "MAINTAIN"
    if quadrant == "FOUNDATIONAL":
        return "PROTECT" if not is_diamond and age_days >= MIN_AGE_DAYS_FOR_PROMOTE else "MAINTAIN"
    if quadrant == "NOISE":
        return "DECAY"
    return "DECAY" if is_diamond else "PURGE" if age_days >= MIN_AGE_DAYS_FOR_PURGE else "DECAY"


def measure_crystal_sync(
    fact_id: str,
    content: str,
    recall_count: int,
    age_days: float,
    is_diamond: bool,
    resonance: float,
    project_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> CrystalVitals:
    temperature = calculate_temperature(recall_count, age_days)
    if resonance >= AXIOMATIC_INERTIA_THRESHOLD and temperature < TEMPERATURE_TIBIA:
        logger.debug(
            "🛡️ [THERMOMETER] Axiomatic Inertia: keeping %s warm (res=%.3f)", fact_id, resonance
        )
        temperature = TEMPERATURE_TIBIA

    quadrant = classify_quadrant(temperature, resonance)
    recommendation = determine_recommendation(
        quadrant, is_diamond, age_days, temperature, resonance
    )

    return CrystalVitals(
        fact_id=fact_id,
        content_preview=content[:100],
        temperature=temperature,
        resonance=resonance,
        quadrant=quadrant,
        recommendation=recommendation,
        age_days=age_days,
        recall_count=recall_count,
        is_diamond=is_diamond,
        project_id=project_id,
        metadata=metadata or {},
    )


async def get_axiom_embeddings(encoder: Any) -> list[list[float]]:
    embeddings = []
    for text in AXIOM_TEXTS:
        try:
            embeddings.append(await encoder.encode(text))
        except Exception as e:
            logger.warning("Failed to encode axiom: %s", e)
    return embeddings


async def scan_all_crystals(
    db_conn: Any,
    encoder: Any | None = None,
    project: str = "autodidact_knowledge",
    tenant_id: str = "sovereign",
) -> list[CrystalVitals]:
    logger.info("🌡️ [THERMOMETER] Scanning crystals for project=%s", project)

    axiom_embeddings = await get_axiom_embeddings(encoder) if encoder else []

    now = time.time()
    vitals = []

    try:
        import numpy as np

        cursor = db_conn.cursor() if hasattr(db_conn, "cursor") else db_conn._get_conn().cursor()

        cursor.execute(
            """
            SELECT f.id, f.content, f.timestamp, f.is_diamond,
                   f.project_id, f.metadata, f.success_rate,
                   v.embedding
            FROM facts_meta f
            JOIN vec_facts v ON f.rowid = v.rowid
            WHERE f.tenant_id = ? AND f.project_id = ?
            ORDER BY f.timestamp DESC
            """,
            (tenant_id, project),
        )

        rows = cursor.fetchall()
        logger.info("🌡️ [THERMOMETER] Found %d crystals to assess", len(rows))

        for row in rows:
            fact_id, content, timestamp, is_diamond, project_id, raw_meta, _, embedding_data = row
            content = content or ""
            timestamp = timestamp or now
            project_id = project_id or project
            metadata = json.loads(raw_meta) if raw_meta else {}

            age_days = max(0.0, (now - timestamp) / 86400.0)

            access_stats = metadata.get("access_stats", {})
            recall_count = access_stats.get("total_access_count", 0)

            resonance = 0.5
            if axiom_embeddings:
                try:
                    embedding = np.frombuffer(embedding_data, dtype=np.float32).tolist()
                    resonance = await calculate_resonance(embedding, axiom_embeddings)
                except Exception:  # noqa: BLE001 — corrupt embedding must not crash scan
                    pass

            vital = measure_crystal_sync(
                fact_id=fact_id,
                content=content,
                recall_count=recall_count,
                age_days=age_days,
                is_diamond=is_diamond,
                resonance=resonance,
                project_id=project_id,
                metadata=metadata,
            )
            vitals.append(vital)

    except Exception as e:
        logger.error("🌡️ [THERMOMETER] Scan failed: %s", e)

    priority_order = {"PURGE": 0, "MERGE": 1, "DECAY": 2, "PROMOTE": 3, "PROTECT": 4, "MAINTAIN": 5}
    vitals.sort(key=lambda v: priority_order.get(v.recommendation, 5))

    quadrant_counts = {}
    for v in vitals:
        quadrant_counts[v.quadrant] = quadrant_counts.get(v.quadrant, 0) + 1

    logger.info(
        "🌡️ [THERMOMETER] Assessment complete: %s",
        " | ".join(f"{q}={c}" for q, c in sorted(quadrant_counts.items())),
    )

    return vitals
