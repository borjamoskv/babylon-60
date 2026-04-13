import pytest

from cortex.api.async_client import AsyncCortexClient
from cortex.api.client import CortexClient, CortexError


def test_sync_client_store_uses_meta_field():
    client = CortexClient()
    captured: dict[str, object] = {}

    def fake_request(method: str, path: str, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs["json"]
        return {"fact_id": 7}

    client._request = fake_request  # type: ignore[method-assign]

    try:
        fact_id = client.store(
            project="demo",
            content="hello",
            fact_type="knowledge",
            metadata={"scope": "public"},
        )
    finally:
        client.close()

    assert fact_id == 7
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/facts"
    assert captured["json"] == {
        "project": "demo",
        "content": "hello",
        "fact_type": "knowledge",
        "tags": [],
        "meta": {"scope": "public"},
    }


@pytest.mark.asyncio
async def test_async_client_store_uses_meta_field():
    client = AsyncCortexClient()
    captured: dict[str, object] = {}

    async def fake_request(method: str, path: str, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["json"] = kwargs["json"]
        return {"fact_id": 11}

    client._request = fake_request  # type: ignore[method-assign]

    try:
        fact_id = await client.store(
            project="demo",
            content="hello",
            fact_type="knowledge",
            metadata={"scope": "public"},
        )
    finally:
        await client.close()

    assert fact_id == 11
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/facts"
    assert captured["json"] == {
        "project": "demo",
        "content": "hello",
        "fact_type": "knowledge",
        "tags": [],
        "source": "",
        "meta": {"scope": "public"},
    }


@pytest.mark.asyncio
async def test_async_client_update_fails_closed_without_patch_route():
    client = AsyncCortexClient()

    try:
        with pytest.raises(CortexError) as excinfo:
            await client.update(7, content="updated")
    finally:
        await client.close()

    assert excinfo.value.status_code == 501
    assert "not exposed on the REST API" in excinfo.value.detail
