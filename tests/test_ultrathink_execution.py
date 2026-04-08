import pytest

from cortex.engine.ultrathink_physics import UltrathinkPhysicsEngine
from cortex.extensions.llm._models import BaseProvider, CortexPrompt, IntentProfile, ReasoningMode
from cortex.extensions.llm.router import CortexLLMRouter


class MockProvider(BaseProvider):
    def __init__(self, name: str, tier: str):
        self._provider_name = name
        self._tier = tier
        self._cost_class = "medium"
        self._context_window = 128000

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def tier(self) -> str:
        return self._tier

    @property
    def cost_class(self) -> str:
        return self._cost_class

    @property
    def context_window(self) -> int:
        return self._context_window

    @property
    def model_name(self) -> str:
        return f"mock-{self._provider_name}"

    async def invoke(self, prompt: CortexPrompt) -> str:
        return f"Mocked {self._provider_name} response"


@pytest.mark.asyncio
async def test_ultrathink_router_coercion():
    """Verify that ULTRA_THINK restricts fallbacks exclusively to frontier tier."""
    primary = MockProvider("gemini-3.1-pro", "frontier")
    fallback_local = MockProvider("llama-7b", "local")
    fallback_high = MockProvider("gpt-4o-mini", "high")
    fallback_frontier = MockProvider("claude-opus", "frontier")

    router = CortexLLMRouter(
        primary=primary, fallbacks=[fallback_local, fallback_high, fallback_frontier]
    )

    prompt = CortexPrompt(
        system_instruction="Simulate architectural collapse",
        working_memory=[],
        intent=IntentProfile.ARCHITECT,
        reasoning_mode=ReasoningMode.ULTRA_THINK,
    )

    # Check ordered fallbacks - Axiom Ω₁₆ mandates ONLY frontier models for ULTRA_THINK
    ordered = router._ordered_fallbacks(prompt)

    assert len(ordered) == 1
    assert ordered[0].provider_name == "claude-opus"

    # Try execution
    res = await router.execute_resilient(prompt)
    assert "Mocked gemini-3.1-pro response" in res.unwrap()


def test_ultrathink_physics_blast_radius():
    """Verify that the Ultrathink Physics Engine correctly computes blast radius and thermodynamic yield."""
    # Graph representing architectural cascade
    dependency_graph = {
        "memory_manager": ["ledger", "vector_store"],
        "vector_store": ["cuda_bridge"],
        "ledger": ["hash_chain"],
        "cuda_bridge": [],
        "hash_chain": [],
    }

    # From memory_manager -> ledger, vector_store, cuda_bridge, hash_chain
    # Nodes: 1 (memory) + 2 (ledger, vector) + 2 (cuda, hash) = 5
    radius = UltrathinkPhysicsEngine.measure_blast_radius(dependency_graph, "memory_manager")
    assert radius == 5

    # Valid execution: high exergy yield (>10.0), adequate blast radius (>=3)
    auth, msg = UltrathinkPhysicsEngine.authorize_ultrathink(
        stochastic_entropy=20.0,
        deterministic_output=150.0,
        execution_time=1.0,
        epicenter_radius=radius,
    )
    assert auth is True
    assert "Horizon Authorized" in msg

    # Invalid execution: blast radius too low
    auth_small, msg_small = UltrathinkPhysicsEngine.authorize_ultrathink(
        stochastic_entropy=20.0, deterministic_output=150.0, execution_time=1.0, epicenter_radius=2
    )
    assert auth_small is False
    assert "too small" in msg_small

    # Invalid execution: exergy yield too low (exergy = 5.0 vs 10.0 req)
    auth_low_exergy, msg_low_exergy = UltrathinkPhysicsEngine.authorize_ultrathink(
        stochastic_entropy=40.0, deterministic_output=50.0, execution_time=2.0, epicenter_radius=5
    )
    assert auth_low_exergy is False
    assert "Insufficient Exergy" in msg_low_exergy
