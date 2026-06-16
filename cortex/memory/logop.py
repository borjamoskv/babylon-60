# [C5-REAL] Exergy-Maximized
"""
Coordination Plane: Logarithmic Opinion Pools (LogOP)

Aggregates belief probabilities across distributed swarm agents
without succumbing to single-node veto annihilation or probability flattening.
"""

from collections.abc import Sequence

from cortex.memory.epistemic_ontology import BeliefObject


def compute_logop_consensus(beliefs: Sequence[BeliefObject], agent_weights: dict[str, float]) -> float:
    """
    Compute the Logarithmic Opinion Pool (LogOP) consensus probability.
    LogOP is strictly multiplicative in log-space to prevent a single node
    from collapsing the swarm consensus to P=0, avoiding malicious vetoes.
    
    Formula:
    P(consensus) = Prod( P_i ^ w_i ) / Z
    Where Z is a normalizing constant. (Simplified here for single-hypothesis bound)
    """
    if not beliefs:
        return 0.0

    log_p_sum = 0.0
    weight_sum = 0.0

    for belief in beliefs:
        signer_id = belief.provenance.signer_id
        # Default weight is 1.0 if agent is unknown, otherwise historical proof-of-expertise
        w_i = agent_weights.get(signer_id, 1.0)
        
        # Prevent math domain error for log(0)
        p_i = max(1e-9, belief.confidence_score)
        
        # Instead of strict log, we compute the exponential pool directly for probability [0, 1]
        import math
        log_p_sum += w_i * math.log(p_i)
        weight_sum += w_i

    if weight_sum == 0.0:
        return 0.0

    # Unnormalized pooled probability (geometric mean weighted by w_i)
    pooled_p = math.exp(log_p_sum / weight_sum)
    
    return pooled_p
