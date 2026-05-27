import pytest
from httpx import AsyncClient

from cortex.api.core import app

@pytest.mark.asyncio
async def test_taas_quote():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        req_data = {
            "task_type": "audit_contract",
            "payload": {"contract_address": "0x123..."},
            "sla": {
                "confidence_level": "C5-REAL",
                "max_latency_ms": 1000,
                "requires_zk_proof": True
            }
        }
        response = await ac.post("/v1/taas/jobs/quote", json=req_data)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "estimated_cost_credits" in data
        assert "estimated_time_ms" in data
        assert data["estimated_cost_credits"] > 0

@pytest.mark.asyncio
async def test_taas_execute_and_verify():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Quote
        req_data = {
            "task_type": "verify_state",
            "payload": {"state_hash": "abc..."},
            "sla": {
                "confidence_level": "C3-SIM",
                "max_latency_ms": 500,
                "requires_zk_proof": False
            }
        }
        quote_res = await ac.post("/v1/taas/jobs/quote", json=req_data)
        assert quote_res.status_code == 200
        job_id = quote_res.json()["job_id"]

        # 2. Execute
        exec_res = await ac.post(f"/v1/taas/jobs/{job_id}/execute")
        assert exec_res.status_code == 200
        exec_data = exec_res.json()
        assert exec_data["status"] == "COMPLETED"
        assert exec_data["job_id"] == job_id
        
        # 3. Verify
        proof = exec_data.get("proof")
        verify_res = await ac.get(f"/v1/taas/jobs/{job_id}/verify", params={"proof": str(proof)})
        assert verify_res.status_code == 200
        assert verify_res.json()["verified"] is True
