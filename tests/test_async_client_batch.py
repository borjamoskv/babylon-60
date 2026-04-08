from __future__ import annotations

import pytest

from cortex.api.async_client import AsyncCortexClient


@pytest.mark.asyncio
async def test_async_client_store_many_uses_batch_route_contract() -> None:
    client = AsyncCortexClient("http://example.test")

    captured: dict[str, object] = {}

    async def fake_request(method: str, path: str, **kwargs: object) -> dict[str, object]:
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs["json"]
        return {"fact_ids": [10, 11], "stored": 2, "errors": [], "total_requested": 2}

    client._request = fake_request  # type: ignore[method-assign]

    result = await client.store_many(
        [
            {
                "project": "alpha",
                "content": "Fact A",
                "fact_type": "decision",
                "tags": ["x"],
                "source": "sdk",
                "meta": {"k": "v"},
                "parent_decision_id": 7,
            },
            {
                "project": "beta",
                "content": "Fact B",
            },
        ]
    )

    assert result == [10, 11]
    assert captured == {
        "method": "POST",
        "path": "/v1/facts/batch",
        "json": {
            "facts": [
                {
                    "project": "alpha",
                    "content": "Fact A",
                    "fact_type": "decision",
                    "tags": ["x"],
                    "source": "sdk",
                    "meta": {"k": "v"},
                    "parent_decision_id": 7,
                },
                {
                    "project": "beta",
                    "content": "Fact B",
                    "fact_type": "knowledge",
                    "tags": [],
                    "source": None,
                    "meta": None,
                    "parent_decision_id": None,
                },
            ]
        },
    }

    await client.close()
