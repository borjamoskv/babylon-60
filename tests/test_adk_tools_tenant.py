from __future__ import annotations

import importlib
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest


@pytest.mark.parametrize(
    "module_name",
    ["cortex.adk.tools", "cortex.extensions.adk.tools"],
)
def test_adk_tools_forward_tenant_and_await_async_engine_methods(
    module_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(module_name)
    calls: list[tuple[str, dict[str, Any]]] = []

    class AsyncOnlyEngine:
        async def store(self, **kwargs: Any) -> int:
            calls.append(("store", kwargs))
            return 41

        async def search(self, **kwargs: Any) -> list[SimpleNamespace]:
            calls.append(("search", kwargs))
            return [
                SimpleNamespace(
                    fact_id=41,
                    score=0.8766,
                    project="cortex",
                    fact_type="knowledge",
                    content="tenant scoped memory",
                )
            ]

        async def stats(self, **kwargs: Any) -> dict[str, Any]:
            calls.append(("stats", kwargs))
            return {"active_facts": 3}

        async def verify_ledger(self, **kwargs: Any) -> dict[str, Any]:
            calls.append(("verify_ledger", kwargs))
            return {"valid": True, "tx_checked": 2, "roots_checked": 1, "violations": []}

        async def deprecate(self, fact_id: int, **kwargs: Any) -> bool:
            calls.append(("deprecate", {"fact_id": fact_id, **kwargs}))
            return True

    engine = AsyncOnlyEngine()

    @contextmanager
    def fake_engine() -> Iterator[AsyncOnlyEngine]:
        yield engine

    monkeypatch.setattr(module, "_sovereign_engine", fake_engine)

    assert module.adk_store(
        project="cortex",
        content="tenant scoped memory",
        tags='["adk", 1, "tenant"]',
        tenant_id="tenant-alpha",
    ) == {
        "status": "success",
        "fact_id": 41,
        "project": "cortex",
        "tenant_id": "tenant-alpha",
    }
    search = module.adk_search("memory", project="cortex", top_k=99, tenant_id="tenant-alpha")
    assert search["status"] == "success"
    assert search["tenant_id"] == "tenant-alpha"
    assert search["results"][0]["score"] == 0.877
    assert module.adk_status(tenant_id="tenant-alpha") == {
        "status": "success",
        "tenant_id": "tenant-alpha",
        "active_facts": 3,
    }
    assert module.adk_ledger_verify(tenant_id="tenant-alpha") == {
        "status": "success",
        "tenant_id": "tenant-alpha",
        "valid": True,
        "transactions_checked": 2,
        "roots_checked": 1,
        "violations": [],
    }
    assert module.adk_deprecate(41, reason="obsolete", tenant_id="tenant-alpha") == {
        "status": "success",
        "fact_id": 41,
        "deprecated": True,
        "tenant_id": "tenant-alpha",
    }

    assert calls == [
        (
            "store",
            {
                "project": "cortex",
                "content": "tenant scoped memory",
                "fact_type": "knowledge",
                "tags": ["adk", "tenant"],
                "confidence": "stated",
                "source": None,
                "tenant_id": "tenant-alpha",
            },
        ),
        (
            "search",
            {
                "query": "memory",
                "project": "cortex",
                "top_k": 20,
                "tenant_id": "tenant-alpha",
            },
        ),
        ("stats", {"tenant_id": "tenant-alpha"}),
        ("verify_ledger", {"tenant_id": "tenant-alpha"}),
        (
            "deprecate",
            {"fact_id": 41, "reason": "obsolete", "tenant_id": "tenant-alpha"},
        ),
    ]


@pytest.mark.parametrize(
    "module_name",
    ["cortex.adk.tools", "cortex.extensions.adk.tools"],
)
def test_adk_tools_reject_blank_tenant_before_engine_use(
    module_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module(module_name)

    @contextmanager
    def forbidden_engine() -> Iterator[None]:
        raise AssertionError("engine should not be opened for invalid tenant")
        yield None

    monkeypatch.setattr(module, "_sovereign_engine", forbidden_engine)

    result = module.adk_store("cortex", "tenant scoped memory", tenant_id=" ")

    assert result["status"] == "error"
    assert "tenant_id must be a non-empty string" in result["message"]


def test_sovereign_engine_awaits_async_lifecycle(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    module = importlib.import_module("cortex.extensions.adk.tools")
    calls: list[tuple[str, Any]] = []

    class AsyncLifecycleEngine:
        def __init__(self, path: str, auto_embed: bool) -> None:
            calls.append(("init", path, auto_embed))

        async def init_db(self) -> None:
            calls.append(("init_db", None))

        async def close(self) -> None:
            calls.append(("close", None))

    db_path = tmp_path / "cortex.db"
    monkeypatch.setenv("CORTEX_DB", str(db_path))
    monkeypatch.setattr(module, "CortexEngine", AsyncLifecycleEngine)

    with module._sovereign_engine() as engine:
        calls.append(("yield", type(engine).__name__))

    assert calls == [
        ("init", str(db_path), False),
        ("init_db", None),
        ("yield", "AsyncLifecycleEngine"),
        ("close", None),
    ]


@pytest.mark.asyncio
async def test_run_engine_method_handles_existing_event_loop() -> None:
    module = importlib.import_module("cortex.extensions.adk.tools")

    class AsyncOnlyEngine:
        async def ping(self) -> str:
            return "pong"

    assert module._run_engine_method(AsyncOnlyEngine(), "ping") == "pong"
