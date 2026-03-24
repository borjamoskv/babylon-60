from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.extensions.llm.provider import LLMProvider
from cortex.extensions.llm.quota import QuotaStatus
from cortex.extensions.llm.router import CortexLLMRouter, IntentProfile


class MockProvider:
    def __init__(self, name, tier, cost_class):
        self.provider_name = name
        self.tier = tier
        self.cost_class = cost_class

    def __repr__(self):
        return f"MockProvider({self.provider_name}, {self.tier}, {self.cost_class})"

@pytest.mark.asyncio
async def test_llm_provider_weighted_acquisition():
    with patch("cortex.extensions.llm.provider.load_presets") as mock_load:
        mock_load.return_value = {
            "high_p": {"base_url": "v", "default_model": "m", "context_window": 1, "cost_class": "high"},
        }
        with patch("cortex.extensions.llm.provider._QUOTA_MANAGER", new_callable=AsyncMock) as mock_qm:
            provider = LLMProvider(provider="high_p", api_key="test")

            # Mock the execute_completion to avoid actual HTTP calls
            with patch.object(provider, "_execute_completion", return_value="ok"):
                await provider.complete("hello")

                # Check that acquire was called with 2.0 tokens (high cost weight)
                mock_qm.acquire.assert_called_with(tokens=2.0)

@pytest.mark.asyncio
async def test_router_reorders_on_low_quota():
    # Setup providers
    p_expensive = MockProvider("expensive_frontier", "frontier", "high")
    p_cheap = MockProvider("cheap_local", "local", "free")

    with patch("cortex.extensions.llm.router._QUOTA_MANAGER") as mock_qm:
        router = CortexLLMRouter(primary=p_expensive, fallbacks=[p_expensive, p_cheap])

        # Mock CascadeManager to make p_expensive "known" and fast
        router._cascade = MagicMock()
        # promote_known_good returns [known] + [unknown]
        # We simulate p_expensive is known (index 0) and p_cheap is unknown (index 1)
        router._cascade.promote_known_good.return_value = [p_expensive, p_cheap]
        router._cascade.get_a_record.side_effect = lambda name: {"latency": 0.1} if name == "expensive_frontier" else None

        # 1. Normal quota (> 20%)
        mock_qm.status.return_value = QuotaStatus(
            capacity=10, current_tokens=5, fill_pct=50.0, refill_rate_per_s=0.1,
            time_to_full_s=50, acquired=0, throttled=0, timeouts=0, throttle_ratio_pct=0
        )

        ordered = router._promote_by_latency_then_cost([p_expensive, p_cheap], IntentProfile.GENERAL)
        # Should be [expensive, cheap] because expensive is "known" and fast
        assert [p.provider_name for p in ordered] == ["expensive_frontier", "cheap_local"]

        # 2. Critical quota (< 20%)
        mock_qm.status.return_value = QuotaStatus(
            capacity=10, current_tokens=1, fill_pct=10.0, refill_rate_per_s=0.1,
            time_to_full_s=90, acquired=0, throttled=0, timeouts=0, throttle_ratio_pct=0
        )

        ordered_low = router._promote_by_latency_then_cost([p_expensive, p_cheap], IntentProfile.GENERAL)
        # Should be [cheap_local, expensive_frontier] because expensive is penalized in conserve mode
        # even if it's "known".
        assert [p.provider_name for p in ordered_low] == ["cheap_local", "expensive_frontier"]

def test_llm_provider_token_weights():
    with patch("cortex.extensions.llm.provider.load_presets") as mock_load:
        mock_load.return_value = {
            "high_p": {"base_url": "v", "default_model": "m", "context_window": 1, "cost_class": "high"},
            "low_p": {"base_url": "v", "default_model": "m", "context_window": 1, "cost_class": "low"},
            "free_p": {"base_url": "v", "default_model": "m", "context_window": 1, "cost_class": "free"},
        }

        # Pass api_key to avoid ValueError
        provider_high = LLMProvider(provider="high_p", api_key="test")
        assert provider_high.token_weight == 2.0

        provider_low = LLMProvider(provider="low_p", api_key="test")
        assert provider_low.token_weight == 0.5

        provider_free = LLMProvider(provider="free_p", api_key="test")
        assert provider_free.token_weight == 0.1
