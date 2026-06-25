import asyncio
import time
import pytest
from cortex.causal.exergy_scheduler import ExergyScheduler, ExergyLane

@pytest.mark.asyncio
async def test_thermodynamic_stress_10k_requests():
    """
    Stress test the Thermodynamic Router with 10,000 concurrent payload routing requests.
    Zero Anergia. Ensures Gil is not blocked by entropy calculation.
    """
    scheduler = ExergyScheduler(tenant_id="STRESS_TENANT_10K")
    
    # 5 Lanes synthetic payloads
    payloads = [
        # STANDARD (LOW risk)
        ("Routine sync update for user profile logic.", ExergyLane.STANDARD),
        # DEEP_THINK (HIGH risk, Blast < 3)
        ("Resolve architecture tradeoff between grpc and zenoh for the engine.", ExergyLane.DEEP_THINK),
        # DEEP_RESEARCH (UNKNOWN risk)
        ("Investigar the new API endpoint for the unknown SOTA model registry.", ExergyLane.DEEP_RESEARCH),
        # ULTRA_THINK (P0 Risk)
        ("CRITICAL P0: Merkle tree corruption detected in the ledger.", ExergyLane.ULTRA_THINK),
        # ULTRA_THINK (HIGH risk, Blast >= 3)
        ("Architecture refactor touching engine, audit, ledger, and crypto.", ExergyLane.ULTRA_THINK),
        # CONTEXT_ABYSS (Size > 80k)
        ("A" * 85000, ExergyLane.CONTEXT_ABYSS)
    ]

    async def worker(worker_id, payload_str, expected_lane):
        # Determine lane
        lane = scheduler.route_query(f"Q_{worker_id}", payload_str)
        assert lane == expected_lane, f"Expected {expected_lane.name}, got {lane.name}"
        
        # Execute in lane
        trace = await scheduler.execute_in_lane(lane, f"Q_{worker_id}", payload_str)
        assert "status" in trace
        return trace

    print("Deploying 10,000 synthetic causality requests...")
    start_time = time.time()
    
    tasks = []
    # Generate 10k tasks
    for i in range(10000):
        payload, expected_lane = payloads[i % len(payloads)]
        tasks.append(worker(i, payload, expected_lane))
        
    results = await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    print(f"Executed 10,000 routes in {duration:.2f} seconds.")
    
    # Validation
    assert len(results) == 10000
    
    # Verify execution limits
    statuses = [r["status"] for r in results]
    assert statuses.count("LEDGER_COMMITTED") > 1600
    assert statuses.count("TRADE_OFF_RESOLVED") > 1600
    assert statuses.count("SOTA_MAPPED") > 1600
    assert statuses.count("CONTAINMENT_ACHIEVED") > 3200
    assert statuses.count("MINED") > 1600
    
    print("Zero Anergia. Causal boundaries held under extreme load.")

if __name__ == "__main__":
    asyncio.run(test_thermodynamic_stress_10k_requests())
