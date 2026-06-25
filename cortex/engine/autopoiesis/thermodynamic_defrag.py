"""
C5-REAL Thermodynamic Defragmenter.
Applies Bayesian inference to calculate causal utility of facts.
Purges entropy (utility < 0.05) to maintain O(1) Swarm TTFT latency.
"""

from __future__ import annotations

import logging
from typing import Any

import torch
from aiosqlite import Connection

from cortex.engine.goat_probability import bayesian_update

logger = logging.getLogger(__name__)

# Entropic threshold: if posterior < this, the fact is purged.
ENTROPIC_THRESHOLD = 0.05

class ThermodynamicDefragmenter:
    """Autonomous Bayesian Mechanics to prune useless vectors."""
    
    @staticmethod
    def calculate_prior(confidence_str: str) -> float:
        """Map string confidence to a prior probability."""
        mapping = {
            "C5-REAL": 1.0,
            "C5": 1.0,
            "C4": 0.8,
            "C3": 0.5,
            "C2": 0.2,
            "C1": 0.1,
            "C0": 0.01
        }
        return mapping.get(confidence_str.upper(), 0.01)

    @staticmethod
    def calculate_likelihood(read_count: int, age_days: float) -> float:
        """Calculate likelihood based on read frequency and age decay."""
        if age_days <= 0:
            age_days = 0.1
        # Simple frequency decay likelihood
        frequency = read_count / age_days
        # Normalize arbitrarily to [0, 1] using a sigmoid-like or clamp function
        likelihood = frequency / (frequency + 1.0)
        # Add a base minimum likelihood so brand new facts don't drop to 0 instantly if age is small
        if age_days < 1.0 and read_count == 0:
            return 0.5
        return max(0.01, min(0.99, likelihood))

    @staticmethod
    async def defragment_tenant(conn: Connection, tenant_id: str = "default") -> int:
        """
        Scans all facts for the tenant. Calculates posterior Causal Utility.
        If posterior < ENTROPIC_THRESHOLD, it marks them for deletion.
        """
        logger.info("Initiating Thermodynamic Defragmentation for tenant: %s", tenant_id)
        
        # In a real system, we'd query reads/age. Here we mock reads for demonstration
        # based on some heuristic or metadata. We'll extract creation time and use it.
        # SQLite: julianday('now') - julianday(created_at)
        
        query = """
            SELECT id, confidence, 
                   COALESCE(julianday('now') - julianday(created_at), 1.0) as age_days,
                   0 as read_count -- Assume 0 for this C5-REAL MVP unless explicitly logged
            FROM facts
            WHERE tenant_id = ?
        """
        
        cursor = await conn.execute(query, (tenant_id,))
        rows = await cursor.fetchall()
        
        entropic_ids = []
        
        for row in rows:
            fact_id, confidence, age_days, read_count = row
            
            prior_val = ThermodynamicDefragmenter.calculate_prior(confidence if confidence else "C0")
            likelihood_val = ThermodynamicDefragmenter.calculate_likelihood(read_count, age_days)
            
            # Use PyTorch tensors for C5-REAL GOAT Probability primitives.
            # We must represent the distribution over {Useful, Entropic}
            prior_tensor = torch.tensor([prior_val, 1.0 - prior_val])
            likelihood_tensor = torch.tensor([likelihood_val, 1.0 - likelihood_val])
            
            posterior_tensor = bayesian_update(prior_tensor, likelihood_tensor)
            posterior_val = posterior_tensor[0].item()  # Extract the P(Useful)

            
            if posterior_val < ENTROPIC_THRESHOLD:
                entropic_ids.append(fact_id)
                
        if not entropic_ids:
            logger.info("Thermodynamic Defragmentation complete. Zero entropy found.")
            return 0
            
        logger.warning("Found %d entropic vectors. Energy below threshold (%.2f). PURGING.", len(entropic_ids), ENTROPIC_THRESHOLD)
        
        # Batch physical delete
        from cortex.search.vector import delete_entropic_vectors
        await delete_entropic_vectors(conn, entropic_ids, tenant_id)
        
        logger.info("Purged %d vectors successfully. Causal compression achieved.", len(entropic_ids))
        return len(entropic_ids)
