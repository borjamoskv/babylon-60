"""
Middleware Termodinámico - Ouroboros Capital Engine
Aplica la regla de Opex: EV (Expected Value) > 10x Compute Cost.
"""


class ExergyGate:
    def __init__(self):
        self.min_target_yield = 500.0
        self.roi_multiplier_threshold = 10.0

    def evaluate_target(self, expected_yield: float, estimated_compute_cost: float) -> dict:
        if expected_yield < self.min_target_yield:
            return {
                "approved": False,
                "reason": f"Expected yield ${expected_yield} below threshold ${self.min_target_yield}",
            }

        if estimated_compute_cost <= 0:
            return {"approved": True, "reason": "Zero exergy cost"}

        roi = expected_yield / estimated_compute_cost
        if roi < self.roi_multiplier_threshold:
            return {
                "approved": False,
                "reason": f"ROI {roi:.1f}x below threshold {self.roi_multiplier_threshold}x",
            }

        return {"approved": True, "reason": "Target clears exergy gate"}
