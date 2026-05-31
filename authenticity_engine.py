import json
from dataclasses import dataclass
from typing import Any


@dataclass
class RawFeatures:
    """
    1. RAW FEATURE LAYER: Semantic-free data signals.
    Numbers derived directly from metadata and API telemetry.
    """

    creator_autonomy: float  # Derived from upload entropy, title variance (0-1)
    algorithmic_pressure: float  # Derived from title_clickbait_ratio, sentiment_volatility (0-1)
    audience_capture: float  # Derived from semantic alignment with comment clusters (0-1)
    creative_entropy: float  # Variance in video duration, formatting, topic drift (0-1)
    monetization_coupling: float  # Derived from sponsor blocks, CTA frequency, Patreon links (0-1)


class AuthenticityDynamicsEngine:
    """
    2. SCORING LAYER: Blind Model.
    Evaluates authenticity as an emergent, time-dependent state.
    A(t) = f(Creator, Algorithm, Audience, Monetization Pressure, Time)
    """

    def __init__(self):
        self.weights = {
            "autonomy": 0.25,
            "alg_pressure_inv": 0.25,
            "aud_capture_inv": 0.20,
            "entropy": 0.20,
            "monetization_inv": 0.10,
        }

    def system_dynamics(self, features: RawFeatures) -> float:
        score = (
            self.weights["autonomy"] * features.creator_autonomy
            + self.weights["alg_pressure_inv"] * (1.0 - features.algorithmic_pressure)
            + self.weights["aud_capture_inv"] * (1.0 - features.audience_capture)
            + self.weights["entropy"] * features.creative_entropy
            + self.weights["monetization_inv"] * (1.0 - features.monetization_coupling)
        )
        return round(score, 4)


class InterpretationLayer:
    """
    3. INTERPRETATION LAYER: Post-hoc labeling and Edge Case routing.
    """

    @staticmethod
    def assign_label(score: float, features: RawFeatures) -> dict[str, Any]:
        edge_cases = []
        # Edge Case 1: Fake Authenticity (High organic aesthetic, high monetization coupling)
        if features.creative_entropy > 0.7 and features.monetization_coupling > 0.8:
            edge_cases.append(
                "Fake Authenticity System (Anti-influencer persona but highly coupled)"
            )

        # Edge Case 2: Silent High-Auth (Low frequency, high autonomy)
        if features.creator_autonomy > 0.8 and features.creative_entropy < 0.3:
            edge_cases.append("Silent High-Auth System (Requires time-normalization)")

        # Edge Case 3: Algorithmic Saints
        if features.algorithmic_pressure > 0.8 and features.audience_capture < 0.3:
            edge_cases.append("Algorithmic Saint (Optimized structure, non-captured audience)")

        if score > 0.75:
            label = "Low-Optimization System (Emergent Organic Signal)"
        elif score < 0.40:
            label = "Engagement-Industrial System (Algorithmic Subjugation)"
        else:
            label = "Hybrid Drift System (Critical Convergence Zone)"

        return {"blind_score": score, "assigned_label": label, "detected_anomalies": edge_cases}


if __name__ == "__main__":
    engine = AuthenticityDynamicsEngine()
    interpreter = InterpretationLayer()

    # TELEMETRY STREAM (MOCK DATA)

    # Vector Alpha (Blind telemetry, previously "Frusciante")
    vector_alpha = RawFeatures(
        creator_autonomy=0.92,
        algorithmic_pressure=0.05,
        audience_capture=0.15,
        creative_entropy=0.88,
        monetization_coupling=0.10,
    )

    # Vector Beta (Blind telemetry, previously "Influencer-Industrial")
    vector_beta = RawFeatures(
        creator_autonomy=0.15,
        algorithmic_pressure=0.95,
        audience_capture=0.92,
        creative_entropy=0.10,
        monetization_coupling=0.98,
    )

    # Vector Gamma (Edge Case: The Fake Authentic / Anti-Influencer)
    vector_gamma = RawFeatures(
        creator_autonomy=0.85,
        algorithmic_pressure=0.40,
        audience_capture=0.60,
        creative_entropy=0.75,
        monetization_coupling=0.95,
    )

    # PROCESS PIPELINE
    nodes = {
        "NODE_ALPHA_01": vector_alpha,
        "NODE_BETA_01": vector_beta,
        "NODE_GAMMA_01": vector_gamma,
    }

    for node_id, vector in nodes.items():
        score = engine.system_dynamics(vector)
        result = interpreter.assign_label(score, vector)

        print(f"--- {node_id} ---")
        print(f"RAW VECTORS: {vector}")
        print(json.dumps(result, indent=2))
        print()
