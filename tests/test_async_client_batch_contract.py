import pytest

from cortex.api.async_client import AsyncCortexClient
from cortex.api.client import CortexError


@pytest.mark.asyncio
async def test_store_many_uses_batch_memories_contract():
    client = AsyncCortexClient()
    captured: dict[str, object] = {}

    async def fake_request(method: str, path: str, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs["json"]
        return {"ids": [21, 22]}

    client._request = fake_request  # type: ignore[method-assign]

    try:
        ids = await client.store_many(
            [
                {
                    "project": "demo",
                    "content": "first",
                    "fact_type": "decision",
                    "tags": ["a"],
                    "source": "agent:test",
                    "meta": {"rank": 1},
                    "parent_decision_id": 9,
                },
                {
                    "project": "demo",
                    "content": "second",
                    "type": "knowledge",
                    "metadata": {"rank": 2},
                },
            ]
        )
    finally:
        await client.close()

    assert ids == [21, 22]
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/facts/batch"
    assert captured["json"] == {
        "memories": [
            {
                "project": "demo",
                "content": "first",
                "type": "decision",
                "tags": ["a"],
                "source": "agent:test",
                "metadata": {"rank": 1},
                "parent_decision_id": 9,
            },
            {
                "project": "demo",
                "content": "second",
                "type": "knowledge",
                "tags": [],
                "source": None,
                "metadata": {"rank": 2},
                "parent_decision_id": None,
            },
        ]
    }


@pytest.mark.asyncio
async def test_store_many_accepts_legacy_fact_ids_response():
    client = AsyncCortexClient()

    async def fake_request(method: str, path: str, **kwargs):
        return {"fact_ids": [31, 32]}

    client._request = fake_request  # type: ignore[method-assign]

    try:
        ids = await client.store_many([{"project": "demo", "content": "hello"}])
    finally:
        await client.close()

    assert ids == [31, 32]


@pytest.mark.asyncio
async def test_store_many_fails_closed_when_ids_are_missing():
    client = AsyncCortexClient()

    async def fake_request(method: str, path: str, **kwargs):
        return {"stored": 1}

    client._request = fake_request  # type: ignore[method-assign]

    try:
        with pytest.raises(CortexError) as excinfo:
            await client.store_many([{"project": "demo", "content": "hello"}])
    finally:
        await client.close()

    assert excinfo.value.status_code == 500
    assert excinfo.value.detail == "Batch store response missing ids"
