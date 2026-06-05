import numpy as np
from sklearn.neighbors import KernelDensity
from dataclasses import dataclass
from typing import List, Callable, Any

from cortex.observability.efel import SystemState, encode_state, encode_task

class FailureField:
    def __init__(self, bandwidth=0.8):
        self.kde = KernelDensity(bandwidth=bandwidth)
        self.fitted = False

    def fit(self, X: np.ndarray):
        if len(X) == 0:
            return
        self.kde.fit(X)
        self.fitted = True

    def potential(self, x: np.ndarray) -> float:
        """Energía = log densidad negativa. Mayor densidad de fallo -> Mayor energía potencial."""
        if not self.fitted:
            return 0.0
        # score_samples returns log density
        return -self.kde.score_samples(x.reshape(1, -1))[0]

@dataclass
class Particle:
    task_name: str
    position: np.ndarray
    velocity: np.ndarray
    mass: float
    original_stats: Any

def force(p1: Particle, p2: Particle) -> np.ndarray:
    """Repulsión si compiten por recursos."""
    diff = p1.position - p2.position
    dist = np.linalg.norm(diff) + 1e-6
    return (p1.mass * p2.mass) / dist**2 * (diff / dist)

def total_force(particle: Particle, particles: List[Particle], field: FailureField) -> np.ndarray:
    F = np.zeros_like(particle.position)
    
    for other in particles:
        if other == particle:
            continue
        F += force(particle, other)
        
    # Gradiente del campo de fallo (hacia donde decrece el potencial de fallo)
    if field.fitted:
        eps = 1e-4
        grad = np.zeros_like(particle.position)
        for i in range(len(particle.position)):
            pos_plus = particle.position.copy()
            pos_plus[i] += eps
            pos_minus = particle.position.copy()
            pos_minus[i] -= eps
            grad[i] = (field.potential(pos_plus) - field.potential(pos_minus)) / (2 * eps)
        
        F -= grad
        
    return F

def simulate_field(particles: List[Particle], field: FailureField, steps: int = 50, dt: float = 0.1):
    for _ in range(steps):
        for p in particles:
            F = total_force(p, particles, field)
            p.velocity += (F / p.mass) * dt
            p.position += p.velocity * dt
            # Hysteresis damping
            p.velocity *= 0.92

def energy(particle: Particle, state_vec: np.ndarray, meta: Any, field: FailureField) -> float:
    # We use the particle's converged position to evaluate potential
    # The prompt concatenates task_vec and state_vec. In this simulation, particle position is the combined state.
    U_failure = field.potential(particle.position)
    
    task_var = particle.original_stats.exergy_var
    runtime = particle.original_stats.runtime_mean
    
    U_variance = meta.alpha_risk * task_var
    U_runtime = np.log(runtime + 1)
    
    return float(U_failure + U_variance + U_runtime)
