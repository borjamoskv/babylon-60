from __future__ import annotations

import pytest

from cortex.memory.encoder import AsyncEncoder


class _AsyncEmbedder:
    async def embed(self, text: str) -> list[float]:
        return [float(len(text))]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] for text in texts]

    @property
    def model_identity_hash(self) -> str:
        return "async-embedder"


@pytest.mark.asyncio
async def test_async_encoder_supports_async_embedder_methods() -> None:
    encoder = AsyncEncoder(embedder=_AsyncEmbedder())  # type: ignore[arg-type]

    assert await encoder.encode("hola") == [4.0]
    assert await encoder.encode_batch(["hola", "adios"]) == [[4.0], [5.0]]
