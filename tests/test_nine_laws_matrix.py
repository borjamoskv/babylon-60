import pytest

from cortex.engine.guard_adapters import VerifierGuardAdapter
from cortex.verification.verifier import SovereignVerifier


class TestNineLawsComplianceMatrix:
    """
    Executable Compliance Matrix for the Nine Sovereign Laws (v6.0).
    Every law must be verifiable via AST, runtime behavior, or structural presence.
    """

    @pytest.mark.asyncio
    async def test_law_omega_1_byzantine_frontier(self):
        """
        Ω₁ · La Ley Bizantina: Validates that generative output (LLM) passes
        through a deterministic frontier.
        Proof: The VerifierGuardAdapter intercepts code and execution facts.
        """
        adapter = VerifierGuardAdapter()

        # Simulated LLM hallucinated logic with a bad exit code
        meta_c4_sim = {
            "exit_code": 1,
            "command_id": "test-sim-01",
            "stderr": "Command not found",
            "source": "LLM-Agent",
        }

        with pytest.raises(ValueError, match="Runtime verification failed"):
            await adapter.check(
                content="Execute dark magic",
                project="test",
                fact_type="execution",
                meta=meta_c4_sim,
                conn=None,
            )

    @pytest.mark.asyncio
    async def test_law_omega_6_execution_quarantine(self):
        """
        Ω₆ · La Ley de Ejecución: O(1) Tensor-State Mandate & Strict Quarantine.
        Proof: SovereignVerifier.verify_runtime explicitly marks exit!=0 as QUARANTINED.
        """
        verifier = SovereignVerifier()
        result = verifier.verify_runtime("cmd-123", {"exit_code": 127, "stderr": "SIGSEGV"})

        assert not result.is_valid
        assert result.runtime_status == "QUARANTINED"
        assert result.exit_code == 127
        assert result.violations[0]["id"] == "V-ERR-01"

    @pytest.mark.asyncio
    async def test_law_omega_9_truth_immutable(self):
        """
        Ω₉ · La Ley de la Verdad: C5-REAL vs C4-SIM.
        Proof: verify_runtime only issues proof certificates for exit_code == 0.
        """
        verifier = SovereignVerifier()
        result_c5 = verifier.verify_runtime("cmd-real", {"exit_code": 0, "stdout": "Tx confirmed."})

        assert result_c5.is_valid
        assert result_c5.runtime_status == "SUCCESS"
        assert "RUNTIME_VERIFIED:cmd-real" in result_c5.proof_certificate
