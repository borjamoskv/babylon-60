from __future__ import annotations

import importlib
import sys


def test_ask_route_import_does_not_initialize_quota_runtime() -> None:
    sys.modules.pop("cortex.routes.ask", None)
    sys.modules.pop("cortex.extensions.llm.provider", None)
    sys.modules.pop("cortex.extensions.llm", None)

    importlib.import_module("cortex.routes.ask")
    provider = sys.modules.get("cortex.extensions.llm.provider")

    assert provider is None or provider._quota_manager is None


def test_provider_quota_manager_initializes_lazily(monkeypatch) -> None:
    provider = importlib.import_module("cortex.extensions.llm.provider")
    provider._quota_manager = None
    calls = {"count": 0}

    class DummyQuotaManager:
        def __init__(self) -> None:
            calls["count"] += 1

    monkeypatch.setattr(provider, "SovereignQuotaManager", DummyQuotaManager)

    first = provider._get_quota_manager()
    second = provider._get_quota_manager()

    assert first is second
    assert calls["count"] == 1
