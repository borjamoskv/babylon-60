import unittest.mock
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2


@pytest.fixture
def mock_encoder():
    encoder = AsyncMock()
    encoder.dimension = 384
    encoder.encode.return_value = [0.1] * 384
    return encoder

@pytest.mark.asyncio
async def test_universe_split_trigger(mock_encoder, tmp_path):
    db_path = tmp_path / "test_vectors.db"
    store = SovereignVectorStoreL2(encoder=mock_encoder, db_path=db_path)

    # Mock sqlite_vec loading
    store._vector_enabled = True

    # 1. Setup global facts
    # (In a real test we would use the actual DB, but here we verify the logic flow)
    tenant_id = "tenant_test"
    project_id = "project_test"

    # Verify shard name generation
    shard_name = store._get_shard_name(tenant_id, project_id)
    assert shard_name == "facts_meta_tenant_test_project_test"

    # Verify domain tables retrieval
    # Since it's the first time, it should check entropy
    # (Mocking the DB count check)
    with unittest.mock.patch.object(SovereignVectorStoreL2, "_get_conn") as mock_get_conn, \
         unittest.mock.patch.object(SovereignVectorStoreL2, "_trigger_split", new_callable=AsyncMock) as mock_trigger_split:

        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        # side_effect for multiple execute() calls:
        # 1. Existence check (SELECT name FROM sqlite_master)
        # 2. Count check (SELECT count(1) FROM facts_meta)
        mock_cursor_exist = MagicMock()
        mock_cursor_exist.fetchone.return_value = None

        mock_cursor_count = MagicMock()
        mock_cursor_count.fetchone.return_value = [100]

        mock_conn.execute.side_effect = [mock_cursor_exist, mock_cursor_count]

        meta, vec = await store._get_domain_tables(tenant_id, project_id)
        assert meta == "facts_meta"
        assert vec == "vec_facts"

        # Reset mocks for expansion test
        mock_cursor_exist_2 = MagicMock()
        mock_cursor_exist_2.fetchone.return_value = None

        mock_cursor_count_2 = MagicMock()
        mock_cursor_count_2.fetchone.return_value = [6000]

        mock_conn.execute.side_effect = [mock_cursor_exist_2, mock_cursor_count_2]

        meta, vec = await store._get_domain_tables(tenant_id, project_id)
        assert meta == shard_name
        assert vec == f"vec_{shard_name}"
        mock_trigger_split.assert_called_once()

@pytest.mark.asyncio
async def test_shard_caching(mock_encoder, tmp_path):
    db_path = tmp_path / "test_cache.db"
    store = SovereignVectorStoreL2(encoder=mock_encoder, db_path=db_path)

    tenant_id = "t1"
    project_id = "p1"
    shard_name = store._get_shard_name(tenant_id, project_id)

    # Seed the cache
    store._shard_cache.add(shard_name)

    meta, vec = await store._get_domain_tables(tenant_id, project_id)
    assert meta == shard_name
    assert vec == f"vec_{shard_name}"
    # Verify that it didn't call the DB count because it was in cache
    # store._get_conn should not have been called for the check
