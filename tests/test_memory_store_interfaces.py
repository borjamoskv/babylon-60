from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.memory.hdc.store import HDCVectorStoreL2
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2


@pytest.mark.asyncio
async def test_sqlite_store_upsert_delegates_to_memorize() -> None:
    store = object.__new__(SovereignVectorStoreL2)
    fact = MagicMock()

    with patch.object(SovereignVectorStoreL2, "memorize", new=AsyncMock()) as mock_memorize:
        await SovereignVectorStoreL2.upsert(store, fact)

    mock_memorize.assert_awaited_once_with(fact)


@pytest.mark.asyncio
async def test_hdc_store_upsert_delegates_to_memorize() -> None:
    store = object.__new__(HDCVectorStoreL2)
    fact = MagicMock()

    with patch.object(HDCVectorStoreL2, "memorize", new=AsyncMock()) as mock_memorize:
        await HDCVectorStoreL2.upsert(store, fact)

    mock_memorize.assert_awaited_once_with(fact)
